import type { FeasibilityResult, FinancialResult, ScenarioResult } from "@/app/lib/types";
import StatTile from "./StatTile";

const STATUS_BG = {
  Feasible: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  Marginal: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  "Not feasible": "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
} as const;

export default function SummaryCard({
  feasibility,
  scenario,
  financial,
}: {
  feasibility: FeasibilityResult;
  scenario: ScenarioResult;
  financial: FinancialResult;
}) {
  return (
    <div className="card p-6 sm:p-8 flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-[var(--color-text)]">Feasibility Verdict</h2>
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${STATUS_BG[feasibility.status]}`}
        >
          {feasibility.status} · {feasibility.score}/100
        </span>
      </div>

      <p className="text-sm text-[var(--color-text)]">{feasibility.summary}</p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Scenario" value={scenario.scenario_name.replace(/_/g, " ")} />
        <StatTile
          label="IRR"
          value={financial.irr_percent != null ? `${financial.irr_percent.toFixed(2)}%` : "—"}
          tone={
            financial.irr_percent == null
              ? "default"
              : financial.irr_percent >= 8
                ? "success"
                : financial.irr_percent >= 0
                  ? "warning"
                  : "danger"
          }
        />
        <StatTile
          label="Payback"
          value={financial.payback_year != null ? `${financial.payback_year} yr` : "—"}
        />
        <StatTile label="Load coverage" value={`${(scenario.load_coverage_rate * 100).toFixed(1)}%`} />
      </div>

      {feasibility.reasons.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--color-text)] mb-1.5">Why</h3>
          <ul className="list-disc pl-5 flex flex-col gap-1">
            {feasibility.reasons.map((r, i) => (
              <li key={i} className="text-sm text-[var(--color-text-muted)]">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {feasibility.recommendations.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--color-text)] mb-1.5">Recommendations</h3>
          <ul className="list-disc pl-5 flex flex-col gap-1">
            {feasibility.recommendations.map((r, i) => (
              <li key={i} className="text-sm text-[var(--color-text-muted)]">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
