from base_agent import BaseAgent, FinancialResult, UserInputs, ScenarioResult
import numpy as np

# Diesel: 3.6 kWh/L generation efficiency, 2.68 kg CO2/L combustion
_DIESEL_KWH_PER_LITER = 3.6
_DIESEL_CO2_PER_LITER = 2.68   # kg CO2/L

class FinancialAgent(BaseAgent):
    def __init__(self):
        super().__init__("Financial Calculation Agent")
        self.constants = {
            "op_cost":      0.05,    # misc operating cost fraction
            "pv_deg_rate":  0.005,   # PV output degradation per year (0.5 %/yr)
            "pv_pr":        0.98,    # initial performance ratio
            "ess_rte":      0.90,    # ESS round-trip efficiency
            "tax_rate":     0.1,     # income tax rate
            "pv_cost":      0.35,    # 万元/kWp installed cost (2025 utility-scale, ~$490/kWp)
            "pv_om_cost":   0.007,   # 万元/(kWp·yr) O&M (2% of CAPEX/yr)
            "ess_cost":     0.15,    # 万元/kWh installed cost (2025 LFP, ~$210/kWh)
            "ess_om_cost":  0.003,   # 万元/(kWh·yr) O&M (2% of CAPEX/yr)
            "discount_rate": 0.08,   # WACC for NPV calculation
            "usd_cny_rate": 7.1,     # FX for USD display
        }

    def _calculate_irr(self, cash_flows: list, max_iter: int = 1000, tol: float = 1e-6):
        def npv(rate):
            try:
                return sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
            except (OverflowError, ZeroDivisionError):
                return float("inf")

        def npv_deriv(rate):
            try:
                return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
            except (OverflowError, ZeroDivisionError):
                return float("inf")

        rate = 0.1
        for _ in range(max_iter):
            nv = npv(rate)
            if not isinstance(nv, float) or abs(nv) < tol:
                return rate
            nd = npv_deriv(rate)
            if abs(nd) < 1e-10 or nd == float("inf"):
                return None
            rate -= nv / nd
            if rate < -0.99 or rate > 100:   # guard against divergence
                return None
        return None

    def _find_payback_year(self, cumulative: list) -> int | None:
        for i, v in enumerate(cumulative, start=1):
            if v >= 0:
                return i
        return None

    def run(self, inputs: UserInputs, scenario_result: ScenarioResult) -> FinancialResult:
        self.log("Starting financial calculation")
        c = self.constants

        pv_cap = scenario_result.pv_capacity_est
        ess_cap = scenario_result.ess_capacity_est
        pv_total = scenario_result.pv_total
        surplus = scenario_result.surplus_total
        grid_price = inputs.grid_price

        # ---- CAPEX & O&M ----
        init_cost = (pv_cap * c["pv_cost"] + ess_cap * c["ess_cost"]) * 10000  # CNY
        om_cost   = (pv_cap * c["pv_om_cost"] + ess_cap * c["ess_om_cost"]) * 10000  # CNY/yr

        # ---- Revenue streams ----
        # Off-grid revenue model: value of electricity supplied to load (tariff or diesel replacement).
        # load_coverage_rate × total_daily_load gives kWh supplied per day; × 365 = annual.
        # ESS charges from surplus and discharges at RTE efficiency, adding coverage beyond direct PV.
        load_total_daily = scenario_result.pv_total / max(scenario_result.pv_utilization_rate, 0.01) \
            * scenario_result.load_coverage_rate  # kWh load covered per day
        # Simpler: direct from coverage rate × pv_total+surplus reconstruction not stored;
        # use pv_self (direct PV to load) + ESS discharge (surplus × RTE) as proxy
        pv_self = pv_total - surplus                          # kWh direct PV to load per day
        ess_discharge = surplus * c["ess_rte"]                # kWh ESS covers load per day
        kwh_supplied_daily = pv_self + ess_discharge          # total kWh delivered to load/day
        rev_first_year = grid_price * 365 * kwh_supplied_daily
        # Grid-tie: add feed-in tariff (50% of grid price for export)
        if "Grid-tie" in scenario_result.scenario_name:
            rev_export = grid_price * 0.5 * 365 * scenario_result.grid_export_kwh
            rev_first_year += rev_export

        # ---- Diesel savings ----
        diesel_annual_saving = 0.0
        if inputs.diesel_liters_per_day and inputs.diesel_liters_per_day > 0:
            diesel_kwh_replaced = min(pv_total * 365,
                                      inputs.diesel_liters_per_day * _DIESEL_KWH_PER_LITER * 365)
            liters_saved = diesel_kwh_replaced / _DIESEL_KWH_PER_LITER
            # USD → CNY at ~7.1; stored as CNY
            diesel_annual_saving = liters_saved * inputs.diesel_price_per_liter * 7.1

        # ---- CO₂ avoided ----
        annual_kwh_clean = kwh_supplied_daily * 365
        if inputs.diesel_liters_per_day and inputs.diesel_liters_per_day > 0:
            co2_annual_tons = (inputs.diesel_liters_per_day * 365 * _DIESEL_CO2_PER_LITER) / 1000
        else:
            co2_annual_tons = (annual_kwh_clean * inputs.co2_grid_factor) / 1000
        co2_lifetime_tons = co2_annual_tons * 25

        # ---- 25-year projections with degradation ----
        annual_revenue, cumulative_profit = [], []
        gross_revenue_cny_list, gross_revenue_usd_list = [], []
        net_cashflow_cny_list, net_cashflow_usd_list = [], []
        cumulative_profit_cny_list, cumulative_profit_usd_list = [], []
        cumulative_irr_percent_list = []
        profit_prev = -init_cost
        gross_revenue_cny_year = rev_first_year + diesel_annual_saving

        for n in range(1, 26):
            # PV output degrades 0.5%/yr; performance ratio adjustment
            deg_factor = c["pv_pr"] - (n - 1) * c["pv_deg_rate"]
            rev_n = (rev_first_year + diesel_annual_saving - om_cost) * (1 - c["tax_rate"]) \
                * (1 - c["op_cost"]) * deg_factor
            profit_n = profit_prev + rev_n
            irr_n = self._calculate_irr([-init_cost] + annual_revenue + [rev_n])

            annual_revenue.append(rev_n)
            cumulative_profit.append(profit_n)
            gross_revenue_cny_list.append(gross_revenue_cny_year)
            gross_revenue_usd_list.append(gross_revenue_cny_year / c["usd_cny_rate"])
            net_cashflow_cny_list.append(rev_n)
            net_cashflow_usd_list.append(rev_n / c["usd_cny_rate"])
            cumulative_profit_cny_list.append(profit_n)
            cumulative_profit_usd_list.append(profit_n / c["usd_cny_rate"])
            cumulative_irr_percent_list.append(round(irr_n * 100, 2) if irr_n is not None else None)
            profit_prev = profit_n

        irr = self._calculate_irr([-init_cost] + annual_revenue)
        payback = self._find_payback_year(cumulative_profit)

        # ---- NPV ----
        dr = c["discount_rate"]
        npv_val = -init_cost + sum(r / (1 + dr) ** (i + 1) for i, r in enumerate(annual_revenue))

        result = self.validate_schema({
            "initial_cost_10k":         round(init_cost / 10000, 2),
            "annual_om_cost_10k":       round(om_cost / 10000, 2),
            "first_year_revenue_10k":   round(rev_first_year / 10000, 2),
            "irr_percent":              round(irr * 100, 2) if irr is not None else None,
            "payback_year":             payback,
            "npv_10k":                  round(npv_val / 10000, 2),
            "annual_revenue_list":      [round(r / 10000, 2) for r in annual_revenue],
            "cumulative_profit_list":   [round(p / 10000, 2) for p in cumulative_profit],
            "gross_revenue_cny_list":   [round(v, 2) for v in gross_revenue_cny_list],
            "gross_revenue_usd_list":   [round(v, 2) for v in gross_revenue_usd_list],
            "net_cashflow_cny_list":    [round(v, 2) for v in net_cashflow_cny_list],
            "net_cashflow_usd_list":    [round(v, 2) for v in net_cashflow_usd_list],
            "cumulative_profit_cny_list": [round(v, 2) for v in cumulative_profit_cny_list],
            "cumulative_profit_usd_list": [round(v, 2) for v in cumulative_profit_usd_list],
            "cumulative_irr_percent_list": cumulative_irr_percent_list,
            "diesel_annual_saving_10k": round(diesel_annual_saving / 10000, 2),
            "annual_co2_avoided_tons":  round(co2_annual_tons, 1),
            "lifetime_co2_avoided_tons": round(co2_lifetime_tons, 0),
        }, FinancialResult)

        self.log(f"Financial complete: CAPEX {result.initial_cost_10k} 万CNY | "
                 f"IRR {result.irr_percent}% | Payback yr{result.payback_year} | "
                 f"CO₂ {result.annual_co2_avoided_tons} t/yr")
        return result

