"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FinancialResult } from "@/app/lib/types";
import StatTile from "./StatTile";

export default function FinancialCard({ financial }: { financial: FinancialResult }) {
  const chartData = financial.cumulative_profit_list.map((v, i) => ({
    year: i,
    "Cumulative profit (万元)": Math.round(v * 10) / 10,
  }));

  return (
    <div className="card p-6 sm:p-8 flex flex-col gap-5">
      <h2 className="text-lg font-semibold text-[var(--color-text)]">Financial Analysis</h2>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="CAPEX" value={`¥${financial.initial_cost_10k.toLocaleString()}万`} />
        <StatTile label="Annual O&M" value={`¥${financial.annual_om_cost_10k.toLocaleString()}万`} />
        <StatTile
          label="NPV"
          value={financial.npv_10k != null ? `¥${financial.npv_10k.toLocaleString()}万` : "—"}
          tone={financial.npv_10k == null ? "default" : financial.npv_10k >= 0 ? "success" : "danger"}
        />
        <StatTile
          label="IRR"
          value={financial.irr_percent != null ? `${financial.irr_percent.toFixed(2)}%` : "—"}
        />
      </div>

      {financial.annual_co2_avoided_tons > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <StatTile label="CO2 avoided / yr" value={`${financial.annual_co2_avoided_tons.toFixed(1)} t`} />
          <StatTile label="CO2 avoided (lifetime)" value={`${financial.lifetime_co2_avoided_tons.toFixed(0)} t`} />
          {financial.diesel_annual_saving_10k > 0 && (
            <StatTile label="Diesel savings / yr" value={`¥${financial.diesel_annual_saving_10k.toLocaleString()}万`} />
          )}
        </div>
      )}

      {chartData.length > 1 && (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                label={{ value: "Year", position: "insideBottom", offset: -2, fontSize: 11, fill: "var(--color-text-muted)" }}
              />
              <YAxis tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
              <Tooltip
                contentStyle={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <ReferenceLine y={0} stroke="var(--color-danger)" strokeDasharray="4 3" />
              <Line
                type="monotone"
                dataKey="Cumulative profit (万元)"
                stroke="var(--color-navy)"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
