import type { MonteCarloResult } from "@/app/lib/types";
import StatTile from "./StatTile";

export default function MonteCarloCard({ mc }: { mc: MonteCarloResult }) {
  if (mc.irr_p10 == null || mc.irr_p50 == null || mc.irr_p90 == null) {
    return null;
  }

  return (
    <div className="card p-6 sm:p-8 flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text)]">Probabilistic Risk Assessment</h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          {mc.n_simulations.toLocaleString()} Monte Carlo draws over solar-resource and grid-price
          uncertainty (fixed seed {mc.seed}, reproducible).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="IRR P10" value={`${mc.irr_p10.toFixed(1)}%`} />
        <StatTile label="IRR P50 (median)" value={`${mc.irr_p50.toFixed(1)}%`} />
        <StatTile label="IRR P90" value={`${mc.irr_p90.toFixed(1)}%`} />
        <StatTile
          label="P(IRR > WACC)"
          value={`${(mc.prob_irr_above_wacc * 100).toFixed(1)}%`}
          tone={mc.prob_irr_above_wacc >= 0.5 ? "success" : mc.prob_irr_above_wacc >= 0.2 ? "warning" : "danger"}
        />
      </div>

      {/* P10-P90 range bar */}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs text-[var(--color-text-muted)]">IRR range (P10 – P90)</span>
        <div className="relative h-3 w-full rounded-full bg-[var(--color-bg)] border border-[var(--color-border)]">
          {(() => {
            const min = Math.min(mc.irr_p10!, 0) - 2;
            const max = Math.max(mc.irr_p90!, 0) + 2;
            const span = max - min || 1;
            const left = ((mc.irr_p10! - min) / span) * 100;
            const width = ((mc.irr_p90! - mc.irr_p10!) / span) * 100;
            const medianLeft = ((mc.irr_p50! - min) / span) * 100;
            return (
              <>
                <div
                  className="absolute h-full rounded-full bg-[var(--color-teal)]/40"
                  style={{ left: `${left}%`, width: `${width}%` }}
                />
                <div
                  className="absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded-full bg-[var(--color-navy)]"
                  style={{ left: `${medianLeft}%` }}
                />
              </>
            );
          })()}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <StatTile label="P(NPV > 0)" value={`${(mc.prob_npv_positive * 100).toFixed(1)}%`} />
        <StatTile label="NPV VaR (5%)" value={`¥${mc.npv_p5_var.toLocaleString()}万`} tone="danger" />
      </div>
    </div>
  );
}
