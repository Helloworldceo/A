"use client";

import { useState } from "react";
import InputForm, { type FormValues } from "@/app/components/InputForm";
import ProgressTracker from "@/app/components/ProgressTracker";
import ResultsDashboard from "@/app/components/ResultsDashboard";
import { readSse } from "@/app/lib/sse";
import type { AnalysisResult, StepStatus } from "@/app/lib/types";

type Phase = "idle" | "running" | "done" | "error";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [statuses, setStatuses] = useState<Record<string, StepStatus>>({});
  const [details, setDetails] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // The password field is always shown; the backend no-ops the check when
  // APP_PASSWORD isn't configured, so this is safe to leave on by default.
  const requiresPassword = true;

  async function runAnalysis(values: FormValues) {
    setPhase("running");
    setStatuses({});
    setDetails({});
    setResult(null);
    setErrorMessage(null);

    try {
      // initial_pv_capacity has a non-optional backend schema (defaults to
      // 1000 when the key is absent) -- omit it entirely rather than send
      // an explicit null, which would fail validation.
      const { initial_pv_capacity, ...rest } = values;
      const payload =
        initial_pv_capacity == null ? rest : { ...rest, initial_pv_capacity };

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        setPhase("error");
        setErrorMessage("Incorrect password.");
        return;
      }
      if (!res.ok) {
        setPhase("error");
        setErrorMessage(`Request failed (${res.status}).`);
        return;
      }

      for await (const frame of readSse(res)) {
        if (frame.event === "progress") {
          const { agent, status, detail } = frame.data as { agent: string; status: StepStatus; detail: string };
          setStatuses((s) => ({ ...s, [agent]: status }));
          setDetails((d) => ({ ...d, [agent]: detail }));
        } else if (frame.event === "done") {
          setResult(frame.data as AnalysisResult);
          setPhase("done");
        } else if (frame.event === "error") {
          const { message } = frame.data as { message: string };
          setErrorMessage(message);
          setPhase("error");
        }
      }
    } catch {
      setPhase("error");
      setErrorMessage("Network error — could not reach the analysis service.");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-12 sm:px-6">
      <header className="flex flex-col gap-3">
        <span className="text-sm font-semibold uppercase tracking-wide text-[var(--color-teal)]">
          IAMS
        </span>
        <h1 className="text-3xl font-bold text-[var(--color-text)] sm:text-4xl">
          Intelligent Analysis &amp; Management System
        </h1>
        <p className="max-w-2xl text-[var(--color-text-muted)]">
          Agentic feasibility assessment for off-grid solar-storage projects. Describe the site
          and load in plain language — a twelve-agent pipeline resolves the location, sizes PV
          and battery capacity, runs a 25-year financial model, and quantifies risk with Monte
          Carlo simulation, end to end in seconds.
        </p>
      </header>

      {(phase === "idle" || phase === "error") && (
        <>
          <InputForm onSubmit={runAnalysis} requiresPassword={requiresPassword} submitting={false} />
          {errorMessage && (
            <p className="rounded-lg bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger)]">
              {errorMessage}
            </p>
          )}
        </>
      )}

      {phase === "running" && <ProgressTracker statuses={statuses} details={details} />}

      {phase === "done" && result && (
        <div className="flex flex-col gap-6">
          <button
            onClick={() => setPhase("idle")}
            className="self-start rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-medium text-[var(--color-text)] hover:bg-[var(--color-surface)]"
          >
            ← Run another analysis
          </button>
          <ResultsDashboard result={result} />
        </div>
      )}

      <footer className="mt-auto pt-8 text-center text-xs text-[var(--color-text-muted)]">
        IAMS — Master of Engineering thesis project, School of Software Engineering, USTC.
      </footer>
    </div>
  );
}
