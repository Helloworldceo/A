"use client";

import { useState } from "react";
import type { EssMode, InstallType, UserInputs } from "@/app/lib/types";

const ESS_MODES: EssMode[] = [
  "Off-grid sensitive type",
  "Off-grid non-sensitive type",
  "Grid-tie / self-consumption",
  "Peak-shaving / demand-charge",
];

const INSTALL_TYPES: { value: InstallType; label: string }[] = [
  { value: "roof", label: "Roof-mounted" },
  { value: "ground", label: "Ground-mounted" },
  { value: "hydro", label: "Hydro" },
];

export interface FormValues extends UserInputs {
  password: string;
}

const DEFAULTS: FormValues = {
  password: "",
  project_address: "",
  load_information: "",
  ess_mode: "Off-grid sensitive type",
  fixed_capacity: null,
  install_type: "roof",
  grid_price: 0.9,
  initial_pv_capacity: 1000,
  autonomy_days: 1,
  diesel_liters_per_day: null,
  diesel_price_per_liter: 1.2,
  co2_grid_factor: 0.5,
};

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-[var(--color-text)]">{label}</span>
      {children}
      {hint && <span className="text-xs text-[var(--color-text-muted)]">{hint}</span>}
    </label>
  );
}

const inputClass =
  "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none transition focus:border-[var(--color-teal)] focus:ring-2 focus:ring-[var(--color-teal)]/20";

export default function InputForm({
  onSubmit,
  requiresPassword,
  submitting,
}: {
  onSubmit: (values: FormValues) => void;
  requiresPassword: boolean;
  submitting: boolean;
}) {
  const [values, setValues] = useState<FormValues>(DEFAULTS);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  function validate(): string | null {
    if (values.project_address.trim().length < 3) return "Project address must be at least 3 characters.";
    if (values.load_information.trim().length < 5) return "Load description must be at least 5 characters.";
    if (values.grid_price <= 0) return "Grid price must be greater than 0.";
    if (values.initial_pv_capacity <= 0) return "Initial PV capacity must be greater than 0.";
    if (values.autonomy_days < 0.5 || values.autonomy_days > 7) return "Autonomy days must be between 0.5 and 7.";
    if (requiresPassword && !values.password) return "Password is required.";
    return null;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} className="card p-6 sm:p-8 flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text)]">Project Inputs</h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Describe the site and load in plain language — the system parses it into a full
          feasibility assessment.
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Project address">
          <input
            className={inputClass}
            placeholder="e.g. Nairobi, Kenya"
            value={values.project_address}
            onChange={(e) => update("project_address", e.target.value)}
          />
        </Field>

        <Field label="ESS mode">
          <select
            className={inputClass}
            value={values.ess_mode}
            onChange={(e) => update("ess_mode", e.target.value as EssMode)}
          >
            {ESS_MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>

        <Field
          label="Load description"
          hint="Free text, e.g. &quot;5 AM to 7 AM 1200kW, noon 1000kW, 3-6 PM 900kW&quot;"
        >
          <textarea
            className={`${inputClass} min-h-24 resize-y sm:col-span-2`}
            placeholder="Describe the 24-hour load profile in plain language"
            value={values.load_information}
            onChange={(e) => update("load_information", e.target.value)}
          />
        </Field>

        <Field label="Install type">
          <select
            className={inputClass}
            value={values.install_type}
            onChange={(e) => update("install_type", e.target.value as InstallType)}
          >
            {INSTALL_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Fixed PV capacity (kWp)" hint="Leave blank to let the system propose a capacity">
          <input
            type="number"
            min={0}
            className={inputClass}
            value={values.fixed_capacity ?? ""}
            onChange={(e) => update("fixed_capacity", e.target.value === "" ? null : Number(e.target.value))}
          />
        </Field>

        <Field label="Initial PV capacity baseline (kWp)">
          <input
            type="number"
            min={0.01}
            step="1"
            className={inputClass}
            value={values.initial_pv_capacity}
            onChange={(e) => update("initial_pv_capacity", Number(e.target.value))}
          />
        </Field>

        <Field label="Grid electricity price (¥/kWh)">
          <input
            type="number"
            min={0.01}
            step="0.01"
            className={inputClass}
            value={values.grid_price}
            onChange={(e) => update("grid_price", Number(e.target.value))}
          />
        </Field>

        <Field label="Battery autonomy (days)" hint="0.5 – 7 days of cloudy-weather backup">
          <input
            type="number"
            min={0.5}
            max={7}
            step="0.5"
            className={inputClass}
            value={values.autonomy_days}
            onChange={(e) => update("autonomy_days", Number(e.target.value))}
          />
        </Field>
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced((s) => !s)}
        className="self-start text-sm font-medium text-[var(--color-teal)] hover:underline"
      >
        {showAdvanced ? "Hide" : "Show"} advanced options
      </button>

      {showAdvanced && (
        <div className="grid gap-5 sm:grid-cols-2 border-t border-[var(--color-border)] pt-5">
          <Field label="Current diesel consumption (L/day)" hint="Optional — enables diesel-savings comparison">
            <input
              type="number"
              min={0}
              className={inputClass}
              value={values.diesel_liters_per_day ?? ""}
              onChange={(e) =>
                update("diesel_liters_per_day", e.target.value === "" ? null : Number(e.target.value))
              }
            />
          </Field>
          <Field label="Diesel price (USD/L)">
            <input
              type="number"
              min={0.01}
              step="0.01"
              className={inputClass}
              value={values.diesel_price_per_liter}
              onChange={(e) => update("diesel_price_per_liter", Number(e.target.value))}
            />
          </Field>
          <Field label="Grid emission factor (kg CO2/kWh)">
            <input
              type="number"
              min={0}
              step="0.01"
              className={inputClass}
              value={values.co2_grid_factor}
              onChange={(e) => update("co2_grid_factor", Number(e.target.value))}
            />
          </Field>
        </div>
      )}

      {requiresPassword && (
        <Field label="Access password">
          <input
            type="password"
            className={inputClass}
            value={values.password}
            onChange={(e) => update("password", e.target.value)}
          />
        </Field>
      )}

      {error && (
        <p className="rounded-lg bg-[var(--color-danger-bg)] px-3 py-2 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="self-start rounded-lg bg-[var(--color-navy)] px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {submitting ? "Running analysis…" : "Run Feasibility Analysis"}
      </button>
    </form>
  );
}
