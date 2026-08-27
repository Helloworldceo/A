import type { AIAnalysisResult } from "@/app/lib/types";

export default function AIAnalysisCard({ ai }: { ai: AIAnalysisResult }) {
  return (
    <div className="card p-6 sm:p-8 flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-[var(--color-text)]">AI Analysis</h2>
      <p className="text-sm font-medium text-[var(--color-text)]">{ai.summary}</p>
      <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line">{ai.conclusion}</p>
      {ai.seasonal_risk && (
        <div className="rounded-lg bg-[var(--color-warning-bg)] px-3 py-2 text-sm text-[var(--color-warning)]">
          ⚠ {ai.seasonal_risk}
        </div>
      )}
    </div>
  );
}
