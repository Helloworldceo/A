from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --------------------------
# Core Data Schemas (Enforce Business Rules)
# --------------------------
class UserInputs(BaseModel):
    """Validated user input schema (enforces input rules upfront)"""
    project_address: str = Field(..., min_length=3, description="Full project address")
    load_information: str = Field(..., min_length=5, description="24-hour load data in free text")
    ess_mode: Literal[
        "Off-grid sensitive type",
        "Off-grid non-sensitive type",
        "Grid-tie / self-consumption",
        "Peak-shaving / demand-charge"
    ]
    fixed_capacity: Optional[float] = Field(None, ge=0, description="Fixed PV capacity (kWp), 0/None = proposed capacity")
    install_type: Literal["roof", "ground", "hydro"] = "roof"
    grid_price: float = Field(0.9, gt=0, description="Electricity price (yuan/kWh)")
    initial_pv_capacity: float = Field(1000.0, gt=0, description="Initial baseline PV capacity (kWp)")
    # --- New optional inputs ---
    autonomy_days: float = Field(1.0, ge=0.5, le=7.0, description="Battery autonomy days (cloudy backup)")
    diesel_liters_per_day: Optional[float] = Field(None, ge=0, description="Current diesel consumption (L/day)")
    diesel_price_per_liter: float = Field(1.2, gt=0, description="Diesel price (USD/L)")
    co2_grid_factor: float = Field(0.5, ge=0, description="Grid emission factor (kg CO2/kWh)")

class LoadData(BaseModel):
    """Validated 24-hour load data schema"""
    hourly_load: List[float] = Field(..., description="24-hour load array (0:00-23:00)")
    total_daily_load: float
    max_hourly_load: float

    @field_validator("hourly_load")
    def validate_24_hour_array(cls, v):
        if len(v) != 24:
            raise ValueError(f"Load array must have exactly 24 elements, got {len(v)}")
        if any(x < 0 for x in v):
            raise ValueError("Load values cannot be negative")
        return v

class GeospatialData(BaseModel):
    """Validated geospatial data schema"""
    latitude: float
    longitude: float
    formatted_address: str = ""
    country_name: str = ""
    optimal_azimuth: float = Field(180.0, ge=0, le=360)
    optimal_tilt: float = Field(26.0, ge=0, le=90)

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {v}")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {v}")
        return v

class PVSystemData(BaseModel):
    """Validated PV generation data schema — all fields from Global Solar Atlas"""
    # ---- Derived 24-hour profile (averaged across months) ----
    hourly_pv_avg: List[float] = Field(..., description="24-hour avg PV generation (kWh)")
    hourly_gti_avg: List[float] = Field(..., description="24-hour avg Global Tilted Irradiance (W/m²)")
    total_daily_pv: float
    hourly_pv_surplus: List[float]
    total_daily_surplus: float
    curtailment_rate: float = Field(ge=0, le=1)

    # ---- Annual summary (single values) ----
    annual_pvout_specific: float = Field(..., description="Annual specific yield (kWh/kWp)")
    annual_pvout_total_kwh: float = Field(..., description="Annual total PV output (kWh)")
    annual_dni: float = Field(..., description="Annual Direct Normal Irradiance (kWh/m²)")
    annual_gti: float = Field(..., description="Annual Global Tilted Irradiance (kWh/m²)")

    # ---- Monthly breakdown (12 values each) ----
    monthly_pvout_total_kwh: List[float] = Field(..., description="Monthly PV output (kWh)")
    monthly_pvout_specific: List[float] = Field(..., description="Monthly specific yield (kWh/kWp)")
    monthly_dni: List[float] = Field(..., description="Monthly DNI (kWh/m²)")
    monthly_gti: List[float] = Field(..., description="Monthly GTI (kWh/m²)")

    # ---- Full monthly-hourly matrices (12×24) for scenario calc ----
    matrix_pvout_total: List[List[float]] = Field(..., description="12×24 PV output matrix (kWh)")
    matrix_gti: List[List[float]] = Field(..., description="12×24 GTI matrix (W/m²)")

    @field_validator("hourly_pv_avg", "hourly_pv_surplus", "hourly_gti_avg")
    def validate_24_hour_array(cls, v):
        if len(v) != 24:
            raise ValueError(f"PV array must have exactly 24 elements, got {len(v)}")
        return v

    @field_validator("monthly_pvout_total_kwh", "monthly_pvout_specific", "monthly_dni", "monthly_gti")
    def validate_12_month_array(cls, v):
        if len(v) != 12:
            raise ValueError(f"Monthly array must have exactly 12 elements, got {len(v)}")
        return v

class ScenarioResult(BaseModel):
    """Validated scenario calculation result schema"""
    scenario_name: str
    pv_capacity_est: float
    ess_capacity_est: float
    pv_total: float
    surplus_total: float
    curtailment_rate: float
    pv_utilization_rate: float
    load_coverage_rate: float
    ess_match_ratio: Optional[float]
    # --- New fields ---
    autonomy_days: float = 1.0
    grid_export_kwh: float = 0.0      # Grid-tie: daily export to grid
    peak_shaved_kwh: float = 0.0      # Peak-shaving: daily peak reduction

class FinancialResult(BaseModel):
    """Validated financial calculation result schema"""
    initial_cost_10k: float
    annual_om_cost_10k: float
    first_year_revenue_10k: float
    irr_percent: Optional[float]
    payback_year: Optional[int]
    npv_10k: Optional[float]
    annual_revenue_list: List[float]
    cumulative_profit_list: List[float]
    gross_revenue_cny_list: List[float] = Field(default_factory=list)
    gross_revenue_usd_list: List[float] = Field(default_factory=list)
    net_cashflow_cny_list: List[float] = Field(default_factory=list)
    net_cashflow_usd_list: List[float] = Field(default_factory=list)
    cumulative_profit_cny_list: List[float] = Field(default_factory=list)
    cumulative_profit_usd_list: List[float] = Field(default_factory=list)
    cumulative_irr_percent_list: List[Optional[float]] = Field(default_factory=list)
    # --- New fields ---
    diesel_annual_saving_10k: float = 0.0
    annual_co2_avoided_tons: float = 0.0
    lifetime_co2_avoided_tons: float = 0.0

class SensitivityResult(BaseModel):
    """IRR sensitivity under solar resource and price variations"""
    scenario_name: str
    base_irr: Optional[float]
    irr_solar_minus10: Optional[float]   # solar -10%
    irr_solar_plus10: Optional[float]    # solar +10%
    irr_price_minus20: Optional[float]   # grid price -20%
    irr_price_plus20: Optional[float]    # grid price +20%
    payback_year_base: Optional[int]
    payback_year_worst: Optional[int]

class MonteCarloResult(BaseModel):
    """Probabilistic risk assessment via Monte Carlo simulation over solar-resource
    and grid-price uncertainty. Complements FinancialResult's single point estimate
    with a distribution of outcomes."""
    scenario_name: str
    n_simulations: int
    seed: int
    irr_mean: Optional[float]
    irr_std: Optional[float]
    irr_p10: Optional[float]
    irr_p50: Optional[float]
    irr_p90: Optional[float]
    npv_mean: float
    npv_p5_var: float          # Value-at-Risk: 5th percentile NPV (10k CNY)
    prob_irr_above_wacc: float  # fraction of draws with IRR > discount_rate (WACC)
    prob_npv_positive: float
    irr_samples: List[float] = Field(default_factory=list)

class FeasibilityResult(BaseModel):
    """Deterministic feasibility assessment for the recommended design"""
    status: Literal["Feasible", "Marginal", "Not feasible"]
    score: int = Field(..., ge=0, le=100)
    summary: str
    reasons: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class MultiScenarioComparison(BaseModel):
    """Side-by-side comparison of all 4 scenarios"""
    scenarios: List[str]
    pv_capacities: List[float]
    ess_capacities: List[float]
    coverage_rates: List[float]
    irr_percents: List[Optional[float]]
    initial_costs: List[float]
    co2_savings: List[float]

class AIAnalysisResult(BaseModel):
    """Validated AI analysis result schema (one per scenario)"""
    scenario_name: str
    summary: str = Field(..., description="Brief one-line conclusion")
    conclusion: str = Field(..., description="Full analysis describing PV and ESS matching")
    report: str = Field(..., description="Markdown-formatted PV+ESS analysis report")
    seasonal_risk: str = Field(default="", description="Seasonal irradiance risk warning")

# --------------------------
# Base Agent Class (Shared by All Agents)
# --------------------------
class BaseAgent:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.max_retries = 3
        self.backoff_factor = 2

    def log(self, message: str, level: str = "INFO"):
        """Unified logging for all agents"""
        print(f"[{level}] [{self.agent_name}] {message}")

    def validate_schema(self, data: dict, schema: BaseModel):
        """Unified schema validation with error handling"""
        try:
            validated = schema(**data)
            self.log("Schema validation passed")
            return validated
        except Exception as e:
            self.log(f"Schema validation failed: {str(e)}", "ERROR")
            raise ValueError(f"[{self.agent_name}] Invalid data: {str(e)}")
