# IAMS Web

A Next.js + Python (FastAPI) web app for the IAMS off-grid PV-ESS feasibility
pipeline, deployable on Vercel.

- **Frontend**: Next.js (App Router, TypeScript, Tailwind) — `app/`
- **Backend**: FastAPI, Server-Sent-Events streaming of live agent progress — `api/index.py`
- **Agent pipeline**: copied from `Thesis-revised/Agent.Work/iams_v2/` into `api/iams/` (kept in sync by hand; see note below)

## Local development

1. Install frontend deps: `npm install`
2. Copy `.env.local.example` to `.env.local` and fill in real values (DeepSeek, OpenCage, Global Solar Atlas keys, and a password for `APP_PASSWORD`).
3. Install the Vercel CLI if you don't have it: `npm i -g vercel`
4. Run both frontend and backend together: `vercel dev`
   (this reads `.env.local` automatically and serves `/api/*` via the Python runtime alongside the Next.js app on one port)
5. Open the printed local URL, fill in the form, and run a real analysis to confirm everything works end-to-end.

## Deploying

1. `vercel link` to connect this directory to a Vercel project (creates one if needed).
2. Set the five required environment variables for Production (and Preview) in the Vercel dashboard, or via CLI:
   ```
   vercel env add OPENAI_API_KEY
   vercel env add OPENAI_BASE_URL
   vercel env add OPENCAGE_API_KEY
   vercel env add GLOBAL_SOLAR_ATLAS_BASE_URL
   vercel env add APP_PASSWORD
   ```
3. `vercel --prod` to deploy, or connect the GitHub repo in the Vercel dashboard for auto-deploy on push.

## Keeping the agent pipeline in sync

`api/iams/` is a **copy**, not a symlink, of the agent modules in
`Thesis-revised/Agent.Work/iams_v2/` — this keeps the web app deployable as a
self-contained Vercel project independent of the thesis repo's filesystem
layout. If you change agent logic in `iams_v2/`, re-copy the changed files
into `api/iams/` to keep this deployment current. The files intentionally
copied are: `base_agent.py`, `agents.py`, `workflow_orchestrator.py`,
`geo_agent.py`, `pv_data_agent.py`, `load_data_agent.py`, `scenario_agent.py`,
`scenario_culc_agent.py`, `financial_culc_agent.py`, `sensitivity_agent.py`,
`montecarlo_agent.py`, `ai_analysis_agent.py`, `reporting_agent.py`,
`feasibility_agent.py`. `reproducibility_cli.py` is deliberately **not**
copied — it's a dev/validation script, not part of the live web flow.
