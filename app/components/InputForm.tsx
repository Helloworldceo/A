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
  initial_pv_capacity: null,
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
    if (values.initial_pv_capacity != null && values.initial_pv_capacity <= 0)
      return "Initial PV capacity baseline must be greater than 0 (or left blank).";
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
        <Field
          label="Project address"
          hint="Any geocodable place name or address — used to look up solar irradiance, optimal panel tilt/azimuth, and country for the site. e.g. &quot;Nairobi, Kenya&quot; or &quot;123 Main St, Austin, TX&quot;"
        >
          <input
            className={inputClass}
            placeholder="e.g. Nairobi, Kenya"
            value={values.project_address}
            onChange={(e) => update("project_address", e.target.value)}
          />
        </Field>

        <Field
          label="ESS mode"
          hint="How the site should use its battery: Off-grid sensitive = full backup, no load ever drops; Off-grid non-sensitive = some load shedding tolerated; Grid-tie = offset grid usage while still connected; Peak-shaving = only trim demand-charge peaks."
        >
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
          hint="Free text describing the 24-hour load profile — list the rough time windows and power draw in kW. e.g. &quot;5 AM to 7 AM 1200kW, noon 1000kW, 3-6 PM 900kW, otherwise near zero&quot;"
        >
          <textarea
            className={`${inputClass} min-h-24 resize-y sm:col-span-2`}
            placeholder="Describe the 24-hour load profile in plain language"
            value={values.load_information}
            onChange={(e) => update("load_information", e.target.value)}
          />
        </Field>

        <Field
          label="Install type"
          hint="Where the PV array will be mounted — affects installation cost assumptions in the financial model. e.g. rooftop for a small commercial site, ground-mounted for open land."
        >
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

        <Field
          label="Fixed PV capacity (kWp)"
          hint="Only set this if the PV size is already decided (e.g. a fixed 500 kWp array on an existing roof). Leave blank to let the system propose an optimal capacity instead."
        >
          <input
            type="number"
            min={0}
            placeholder="e.g. 500 (optional)"
            className={inputClass}
            value={values.fixed_capacity ?? ""}
            onChange={(e) => update("fixed_capacity", e.target.value === "" ? null : Number(e.target.value))}
          />
        </Field>

        <Field
          label="Initial PV capacity baseline (kWp)"
          hint="A starting reference size used to pull solar-resource data and seed proposed-capacity sizing. Leave blank to use the system default (1000 kWp) — most users can leave this blank."
        >
          <input
            type="number"
            min={0.01}
            step="1"
            placeholder="e.g. 1000 (optional, defaults to 1000)"
            className={inputClass}
            value={values.initial_pv_capacity ?? ""}
            onChange={(e) =>
              update("initial_pv_capacity", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        </Field>

        <Field
          label="Grid electricity price (¥/kWh)"
          hint="Local retail electricity price, used to value the load served by self-generation. e.g. 0.9 for ¥0.9/kWh."
        >
          <input
            type="number"
            min={0.01}
            step="0.01"
            placeholder="e.g. 0.9"
            className={inputClass}
            value={values.grid_price}
            onChange={(e) => update("grid_price", Number(e.target.value))}
          />
        </Field>

        <Field
          label="Battery autonomy (days)"
          hint="How many days of cloudy-weather backup the battery should provide, between 0.5 and 7. e.g. 1 for a typical 1-day reserve."
        >
          <input
            type="number"
            min={0.5}
            max={7}
            step="0.5"
            placeholder="e.g. 1"
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
          <Field
            label="Current diesel consumption (L/day)"
            hint="Optional — if this site currently runs on a diesel generator, enter its daily fuel use to get a diesel-savings comparison. e.g. 50 (optional, leave blank if not applicable)."
          >
            <input
              type="number"
              min={0}
              placeholder="e.g. 50 (optional)"
              className={inputClass}
              value={values.diesel_liters_per_day ?? ""}
              onChange={(e) =>
                update("diesel_liters_per_day", e.target.value === "" ? null : Number(e.target.value))
              }
            />
          </Field>
          <Field
            label="Diesel price (USD/L)"
            hint="Local diesel fuel price, used together with consumption above to estimate savings from displaced generator use. e.g. 1.2."
          >
            <input
              type="number"
              min={0.01}
              step="0.01"
              placeholder="e.g. 1.2"
              className={inputClass}
              value={values.diesel_price_per_liter}
              onChange={(e) => update("diesel_price_per_liter", Number(e.target.value))}
            />
          </Field>
          <Field
            label="Grid emission factor (kg CO2/kWh)"
            hint="How much CO2 the local grid emits per kWh, used to estimate emissions avoided by self-generation. Typical range 0.4–0.9. e.g. 0.5."
          >
            <input
              type="number"
              min={0}
              step="0.01"
              placeholder="e.g. 0.5"
              className={inputClass}
              value={values.co2_grid_factor}
              onChange={(e) => update("co2_grid_factor", Number(e.target.value))}
            />
          </Field>
        </div>
      )}

      {requiresPassword && (
        <Field label="Access password" hint="The shared password provided to you for accessing this tool.">
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
