// Mirrors the Pydantic schemas in api/iams/base_agent.py -- kept in sync by hand.

export type EssMode =
  | "Off-grid sensitive type"
  | "Off-grid non-sensitive type"
  | "Grid-tie / self-consumption"
  | "Peak-shaving / demand-charge";

export type InstallType = "roof" | "ground" | "hydro";

export interface UserInputs {
  project_address: string;
  load_information: string;
  ess_mode: EssMode;
  fixed_capacity?: number | null;
  install_type: InstallType;
  grid_price: number;
  initial_pv_capacity?: number | null;
  autonomy_days: number;
  diesel_liters_per_day?: number | null;
  diesel_price_per_liter: number;
  co2_grid_factor: number;
}

export interface LoadData {
  hourly_load: number[];
  total_daily_load: number;
  max_hourly_load: number;
}

export interface GeospatialData {
  latitude: number;
  longitude: number;
  formatted_address: string;
  country_name: string;
  optimal_azimuth: number;
  optimal_tilt: number;
}

export interface PVSystemData {
  hourly_pv_avg: number[];
  hourly_gti_avg: number[];
  total_daily_pv: number;
  hourly_pv_surplus: number[];
  total_daily_surplus: number;
  curtailment_rate: number;
  annual_pvout_specific: number;
  annual_pvout_total_kwh: number;
  annual_dni: number;
  annual_gti: number;
  monthly_pvout_total_kwh: number[];
  monthly_pvout_specific: number[];
  monthly_dni: number[];
  monthly_gti: number[];
}

export interface ScenarioResult {
  scenario_name: string;
  pv_capacity_est: number;
  ess_capacity_est: number;
  pv_total: number;
  surplus_total: number;
  curtailment_rate: number;
  pv_utilization_rate: number;
  load_coverage_rate: number;
  ess_match_ratio: number | null;
  autonomy_days: number;
  grid_export_kwh: number;
  peak_shaved_kwh: number;
}

export interface FinancialResult {
  initial_cost_10k: number;
  annual_om_cost_10k: number;
  first_year_revenue_10k: number;
  irr_percent: number | null;
  payback_year: number | null;
  npv_10k: number | null;
  annual_revenue_list: number[];
  cumulative_profit_list: number[];
  diesel_annual_saving_10k: number;
  annual_co2_avoided_tons: number;
  lifetime_co2_avoided_tons: number;
}

export interface SensitivityResult {
  scenario_name: string;
  base_irr: number | null;
  irr_solar_minus10: number | null;
  irr_solar_plus10: number | null;
  irr_price_minus20: number | null;
  irr_price_plus20: number | null;
  payback_year_base: number | null;
  payback_year_worst: number | null;
}

export interface MonteCarloResult {
  scenario_name: string;
  n_simulations: number;
  seed: number;
  irr_mean: number | null;
  irr_std: number | null;
  irr_p10: number | null;
  irr_p50: number | null;
  irr_p90: number | null;
  npv_mean: number;
  npv_p5_var: number;
  prob_irr_above_wacc: number;
  prob_npv_positive: number;
}

export type FeasibilityStatus = "Feasible" | "Marginal" | "Not feasible";

export interface FeasibilityResult {
  status: FeasibilityStatus;
  score: number;
  summary: string;
  reasons: string[];
  recommendations: string[];
}

export interface AIAnalysisResult {
  scenario_name: string;
  summary: string;
  conclusion: string;
  report: string;
  seasonal_risk: string;
}

export interface AnalysisResult {
  validated_inputs: UserInputs;
  load_data: LoadData;
  geospatial_data: GeospatialData;
  pv_system_data: PVSystemData;
  scenario_name: string;
  scenario_result: ScenarioResult;
  ai_analysis: AIAnalysisResult;
  financial_result: FinancialResult;
  sensitivity_result: SensitivityResult;
  montecarlo_result: MonteCarloResult;
  feasibility_result: FeasibilityResult;
  markdown_report: string;
}

export type StepStatus = "pending" | "running" | "done" | "error";

export interface ProgressEvent {
  agent: string;
  status: "running" | "done" | "error";
  detail: string;
}

// Real step order as reported by workflow_orchestrator.py's progress_callback.
export const PIPELINE_STEPS = [
  "Input Validation",
  "Load Extraction",
  "Geospatial",
  "PV Data",
  "Scenario Router",
  "Scenario Calculation",
  "AI Analysis",
  "Financial",
  "Sensitivity",
  "Monte Carlo",
  "Feasibility",
  "Report",
] as const;
