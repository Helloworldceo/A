from base_agent import BaseAgent, UserInputs, LoadData, GeospatialData, PVSystemData, ScenarioResult, AIAnalysisResult, FinancialResult, MonteCarloResult
import pandas as pd


def _compact_num(v: float) -> str:
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{v / 1_000_000_000:.2f} billion"
    if a >= 1_000_000:
        return f"{v / 1_000_000:.2f} million"
    if a >= 1_000:
        return f"{v / 1_000:.2f} thousand"
    return f"{v:.2f}"


def _money_pair(cny: float, fx: float = 7.1) -> str:
    usd = cny / fx
    return f"CNY {_compact_num(cny)} | USD {_compact_num(usd)}"


def _format_percent(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}%"


def _format_cny(value: float) -> str:
    return f"CNY {value:,.0f}"


def _projection_milestones_df(financial: FinancialResult) -> pd.DataFrame:
    milestone_years = [1, 5, 10, 15, 20, 25]
    rows = []
    for year in milestone_years:
        idx = year - 1
        rows.append({
            "Year": f"Year {year}",
            "Gross Revenue": _format_cny(financial.gross_revenue_cny_list[idx]),
            "Net Cash Flow": _format_cny(financial.net_cashflow_cny_list[idx]),
            "Cumulative Profit": _format_cny(financial.cumulative_profit_cny_list[idx]),
            "Cumulative IRR": _format_percent(financial.cumulative_irr_percent_list[idx]),
        })
    return pd.DataFrame(rows)

class ReportingAgent(BaseAgent):
    def __init__(self):
        super().__init__("Reporting Agent")

    def _montecarlo_section(self, mc: "MonteCarloResult | None") -> str:
        if mc is None:
            return ""
        wacc = 8.0
        return f"""
## Probabilistic Risk Assessment (Monte Carlo, N={mc.n_simulations})
| Metric | Value |
|---|---|
| IRR P10 / P50 / P90 | {_format_percent(mc.irr_p10)} / {_format_percent(mc.irr_p50)} / {_format_percent(mc.irr_p90)} |
| IRR mean (std dev) | {_format_percent(mc.irr_mean)} ({_format_percent(mc.irr_std)}) |
| Probability IRR > {wacc:.0f}% WACC | {mc.prob_irr_above_wacc:.1%} |
| Probability NPV > 0 | {mc.prob_npv_positive:.1%} |
| NPV Value-at-Risk (5th pct.) | {_money_pair(mc.npv_p5_var * 10000)} |
"""

    def generate_markdown_report(
        self,
        inputs: UserInputs,
        load: LoadData,
        geo: GeospatialData,
        pv: PVSystemData,
        scenario: ScenarioResult,
        ai_analysis: AIAnalysisResult,
        financial: FinancialResult,
        montecarlo: MonteCarloResult | None = None
    ) -> str:
        """Generate structured Markdown report with AI analysis section"""
        self.log("Generating final report")

        revenue_table = _projection_milestones_df(financial).to_markdown(index=False)

        report = f"""# PV+ESS Intelligent Solution Report

## Project Overview
| Field | Value |
|---|---|
| Project Address | {geo.formatted_address or inputs.project_address} |
| Coordinates | {geo.latitude}°N, {geo.longitude}°E |
| Installation Type | {inputs.install_type} |
| ESS Mode | {inputs.ess_mode} |
| Scenario | {scenario.scenario_name} |

## Solar Resource Data (Global Solar Atlas)
| Metric | Value |
|---|---|
| Annual Specific Yield | {pv.annual_pvout_specific:.1f} kWh/kWp |
| Annual Total PV Output | {pv.annual_pvout_total_kwh:,.0f} kWh |
| Annual GTI | {pv.annual_gti:.1f} kWh/m² |
| Annual DNI | {pv.annual_dni:.1f} kWh/m² |

## Core System Configuration
| Parameter | Value |
|---|---|
| Recommended PV Capacity | {scenario.pv_capacity_est} kWp |
| Recommended ESS Capacity | {scenario.ess_capacity_est} kWh |
| Optimal Azimuth Angle | {geo.optimal_azimuth}° |
| Optimal Tilt Angle | {geo.optimal_tilt}° |

## System Performance Metrics
| Metric | Value |
|---|---|
| Total Daily PV Generation | {scenario.pv_total} kWh |
| Total Daily PV Surplus | {scenario.surplus_total} kWh |
| Curtailment Rate | {round(scenario.curtailment_rate * 100, 2)}% |
| PV Utilization Rate | {round(scenario.pv_utilization_rate * 100, 2)}% |
| Load Coverage Rate | {round(scenario.load_coverage_rate * 100, 2)}% |
| ESS Match Ratio | {round(scenario.ess_match_ratio, 3) if scenario.ess_match_ratio else "N/A"} |

## Load Profile Summary
| Metric | Value |
|---|---|
| Total Daily Load | {load.total_daily_load} kWh |
| Maximum Hourly Load | {load.max_hourly_load} kW |

## AI System Analysis
> **{ai_analysis.summary}**

{ai_analysis.report}

## Financial Analysis
| Metric | Value |
|---|---|
| Initial Investment Cost | {_money_pair(financial.initial_cost_10k * 10000)} |
| Annual O&M Cost | {_money_pair(financial.annual_om_cost_10k * 10000)} per year |
| First-Year Total Revenue | {_money_pair(financial.first_year_revenue_10k * 10000)} |
| 25-Year IRR | {_format_percent(financial.irr_percent)} |
| Payback Period | {"Year " + str(financial.payback_year) if financial.payback_year else "N/A"} |
| NPV (25yr @ 8%) | {_money_pair(financial.npv_10k * 10000) if financial.npv_10k is not None else "N/A"} |
{self._montecarlo_section(montecarlo)}
## Environmental Impact
| Metric | Value |
|---|---|
| Annual CO₂ Avoided | {financial.annual_co2_avoided_tons} t/yr |
| Lifetime CO₂ Avoided (25yr) | {financial.lifetime_co2_avoided_tons:.0f} t |
{f"| Annual Diesel Saving | {financial.diesel_annual_saving_10k:.2f} 万元/yr |" if financial.diesel_annual_saving_10k and financial.diesel_annual_saving_10k > 0 else ""}

### 25-Year Revenue & Profit Projection
Milestone years are shown below for readability. The full year-by-year table remains available in the app.

{revenue_table}

---
*Generated by IAMS — PV+ESS Intelligent Solution Assistant (v2.1)*
"""
        return report

    def run(
        self,
        inputs: UserInputs,
        load: LoadData,
        geo: GeospatialData,
        pv: PVSystemData,
        scenario: ScenarioResult,
        ai_analysis: AIAnalysisResult,
        financial: FinancialResult,
        montecarlo: MonteCarloResult | None = None
    ) -> tuple:
        """Run full reporting pipeline"""
        markdown_report = self.generate_markdown_report(inputs, load, geo, pv, scenario, ai_analysis, financial, montecarlo)

        summary_data = {
            "Parameter": [
                "PV Capacity (kWp)", "ESS Capacity (kWh)", "Curtailment Rate (%)",
                "Load Coverage Rate (%)", "Initial Cost (万元)", "IRR (%)",
                "Payback Year", "NPV 25yr (万元)", "CO₂ Avoided (t/yr)"
            ],
            "Value": [
                scenario.pv_capacity_est,
                scenario.ess_capacity_est,
                round(scenario.curtailment_rate * 100, 2),
                round(scenario.load_coverage_rate * 100, 2),
                financial.initial_cost_10k,
                _format_percent(financial.irr_percent),
                financial.payback_year,
                financial.npv_10k,
                financial.annual_co2_avoided_tons,
            ]
        }
        summary_df = pd.DataFrame(summary_data)

        self.log("Report generation complete")
        return markdown_report, summary_df
