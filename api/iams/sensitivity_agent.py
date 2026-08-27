"""
sensitivity_agent.py
────────────────────
Runs IRR sensitivity analysis (±10% solar, ±20% price) and
detects seasonal irradiance risk from the monthly GSA data.

All calculations reuse FinancialAgent logic without API calls.
"""

from base_agent import BaseAgent, SensitivityResult, UserInputs, ScenarioResult, PVSystemData
from financial_culc_agent import FinancialAgent


class SensitivityAgent(BaseAgent):
    def __init__(self):
        super().__init__("Sensitivity Analysis Agent")
        self._fin = FinancialAgent()

    # ------------------------------------------------------------------
    # IRR for a scaled version of the scenario
    # ------------------------------------------------------------------
    def _irr_for(self, inputs: UserInputs, scenario: ScenarioResult,
                 solar_scale: float = 1.0, price_scale: float = 1.0) -> float | None:
        """Re-run financial calc with scaled solar output and grid price."""
        from base_agent import ScenarioResult as SR
        scaled = SR(
            scenario_name=scenario.scenario_name,
            pv_capacity_est=scenario.pv_capacity_est,
            ess_capacity_est=scenario.ess_capacity_est,
            pv_total=scenario.pv_total * solar_scale,
            surplus_total=scenario.surplus_total * solar_scale,
            curtailment_rate=scenario.curtailment_rate,
            pv_utilization_rate=scenario.pv_utilization_rate,
            load_coverage_rate=scenario.load_coverage_rate,
            ess_match_ratio=scenario.ess_match_ratio,
            autonomy_days=scenario.autonomy_days,
            grid_export_kwh=scenario.grid_export_kwh * solar_scale,
            peak_shaved_kwh=scenario.peak_shaved_kwh,
        )
        from base_agent import UserInputs as UI
        scaled_inputs = inputs.model_copy(update={"grid_price": inputs.grid_price * price_scale})
        try:
            fin = self._fin.run(scaled_inputs, scaled)
            return fin.irr_percent
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Seasonal irradiance risk
    # ------------------------------------------------------------------
    def detect_seasonal_risk(self, pv: PVSystemData) -> str:
        """
        Flag if the worst month is <60% of the best month's specific yield.
        Returns a plain-language warning string (empty = no significant risk).
        """
        monthly = pv.monthly_pvout_specific
        if not monthly or len(monthly) < 12:
            return ""
        best = max(monthly)
        worst = min(monthly)
        ratio = worst / best if best > 0 else 1.0
        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        worst_month = months[monthly.index(worst)]
        best_month  = months[monthly.index(best)]
        if ratio < 0.60:
            return (f"⚠️ Strong seasonal variation: {worst_month} yield "
                    f"({worst:.1f} kWh/kWp) is only {ratio*100:.0f}% of "
                    f"{best_month} ({best:.1f} kWh/kWp). "
                    f"Battery autonomy should cover at least {round(1/ratio, 1)} days. "
                    f"Consider upsizing ESS for cloudy-season resilience.")
        if ratio < 0.80:
            return (f"⚠️ Moderate seasonal variation: {worst_month} yield "
                    f"({worst:.1f} kWh/kWp) is {ratio*100:.0f}% of peak. "
                    f"Verify ESS autonomy covers low-irradiance months.")
        return ""

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def run(self, inputs: UserInputs, scenario: ScenarioResult,
            pv: PVSystemData) -> SensitivityResult:
        self.log(f"Running sensitivity analysis for: {scenario.scenario_name}")

        base_irr        = self._irr_for(inputs, scenario, 1.0, 1.0)
        irr_sol_m10     = self._irr_for(inputs, scenario, 0.9, 1.0)
        irr_sol_p10     = self._irr_for(inputs, scenario, 1.1, 1.0)
        irr_price_m20   = self._irr_for(inputs, scenario, 1.0, 0.8)
        irr_price_p20   = self._irr_for(inputs, scenario, 1.0, 1.2)

        # Payback for base and worst case (solar -10% + price -20%)
        def _payback(solar_scale, price_scale):
            from base_agent import ScenarioResult as SR, UserInputs as UI
            scaled_s = scenario.model_copy(update={
                "pv_total": scenario.pv_total * solar_scale,
                "surplus_total": scenario.surplus_total * solar_scale,
                "grid_export_kwh": scenario.grid_export_kwh * solar_scale,
            })
            scaled_i = inputs.model_copy(update={"grid_price": inputs.grid_price * price_scale})
            try:
                fin = self._fin.run(scaled_i, scaled_s)
                return fin.payback_year
            except Exception:
                return None

        payback_base  = _payback(1.0, 1.0)
        payback_worst = _payback(0.9, 0.8)

        result = self.validate_schema({
            "scenario_name":    scenario.scenario_name,
            "base_irr":         base_irr,
            "irr_solar_minus10": irr_sol_m10,
            "irr_solar_plus10":  irr_sol_p10,
            "irr_price_minus20": irr_price_m20,
            "irr_price_plus20":  irr_price_p20,
            "payback_year_base":  payback_base,
            "payback_year_worst": payback_worst,
        }, SensitivityResult)

        self.log(f"Sensitivity done: base IRR {base_irr}% | "
                 f"worst-case IRR {irr_sol_m10}% | payback base yr{payback_base}")
        return result
