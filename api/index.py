"""
FastAPI backend for IAMS on Vercel.

Wraps the existing iams_v2 agent pipeline (copied into ./iams/) behind two
endpoints:
  GET  /api/health   - liveness check
  POST /api/analyze  - runs the full agent workflow and streams live
                        per-agent progress over Server-Sent Events, ending
                        with a `done` event carrying the full result payload.

The agent pipeline's own `progress_callback` hook (see
iams/workflow_orchestrator.py) already reports each of the ~11 real steps as
they happen; this file streams those events to the browser rather than
faking a spinner.
"""
import json
import os
import queue
import sys
import threading
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "iams"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from workflow_orchestrator import PVESSWorkflowOrchestrator  # noqa: E402

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _to_plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(request: Request):
    body = await request.json()

    expected_password = os.environ.get("APP_PASSWORD")
    submitted_password = body.pop("password", None)
    if expected_password and submitted_password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    def generate():
        q: "queue.Queue" = queue.Queue()

        def progress_callback(name: str, status: str, detail: str = ""):
            q.put(("progress", {"agent": name, "status": status, "detail": detail}))

        def worker():
            try:
                orchestrator = PVESSWorkflowOrchestrator()
                result = orchestrator.run_full_workflow(body, progress_callback=progress_callback)
                if result.get("success"):
                    payload = {
                        key: _to_plain(value)
                        for key, value in result.items()
                        if key not in ("success", "summary_df")
                    }
                    q.put(("done", payload))
                else:
                    q.put(("error", {"message": result.get("error_message", "Unknown error")}))
            except Exception as exc:  # surface a clean error event instead of a raw 500
                q.put(("error", {"message": str(exc), "trace": traceback.format_exc()}))
            finally:
                q.put((None, None))

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event, data = q.get()
            if event is None:
                break
            yield _sse(event, data)

    return StreamingResponse(generate(), media_type="text/event-stream")
