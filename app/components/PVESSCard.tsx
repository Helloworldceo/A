"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { LoadData, PVSystemData, ScenarioResult } from "@/app/lib/types";
import StatTile from "./StatTile";

export default function PVESSCard({
  scenario,
  load,
  pv,
}: {
  scenario: ScenarioResult;
  load: LoadData;
  pv: PVSystemData;
}) {
  const chartData = Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    "PV generation (kW)": Math.round(pv.hourly_pv_avg[h] ?? 0),
    "Load demand (kW)": Math.round(load.hourly_load[h] ?? 0),
  }));

  return (
    <div className="card p-6 sm:p-8 flex flex-col gap-5">
      <h2 className="text-lg font-semibold text-[var(--color-text)]">PV &amp; Energy Storage</h2>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="PV capacity" value={`${scenario.pv_capacity_est.toLocaleString()} kWp`} />
        <StatTile label="ESS capacity" value={`${scenario.ess_capacity_est.toLocaleString()} kWh`} />
        <StatTile label="Curtailment" value={`${(scenario.curtailment_rate * 100).toFixed(1)}%`} />
        <StatTile label="PV utilisation" value={`${(scenario.pv_utilization_rate * 100).toFixed(1)}%`} />
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="hour"
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
              ticks={[0, 3, 6, 9, 12, 15, 18, 21]}
              label={{ value: "Hour of day", position: "insideBottom", offset: -2, fontSize: 11, fill: "var(--color-text-muted)" }}
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
            <Line type="monotone" dataKey="PV generation (kW)" stroke="var(--color-gold)" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Load demand (kW)" stroke="var(--color-teal)" strokeWidth={2} dot={false} strokeDasharray="4 3" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
