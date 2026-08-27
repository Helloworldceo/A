"use client";

import { PIPELINE_STEPS, type StepStatus } from "@/app/lib/types";

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "done") {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-success)] text-white text-xs">
        ✓
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="flex h-5 w-5 items-center justify-center">
        <span className="h-3 w-3 animate-pulse rounded-full bg-[var(--color-teal)]" />
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-danger)] text-white text-xs">
        !
      </span>
    );
  }
  return <span className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-[var(--color-border)]" />;
}

export default function ProgressTracker({
  statuses,
  details,
}: {
  statuses: Record<string, StepStatus>;
  details: Record<string, string>;
}) {
  return (
    <div className="card p-6 sm:p-8">
      <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">Running Analysis</h2>
      <ul className="flex flex-col gap-3">
        {PIPELINE_STEPS.map((step) => {
          const status = statuses[step] ?? "pending";
          return (
            <li key={step} className="flex items-center gap-3">
              <StatusIcon status={status} />
              <div className="flex flex-col">
                <span
                  className={`text-sm ${
                    status === "pending" ? "text-[var(--color-text-muted)]" : "text-[var(--color-text)] font-medium"
                  }`}
                >
                  {step}
                </span>
                {details[step] && (
                  <span className="text-xs text-[var(--color-text-muted)]">{details[step]}</span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
