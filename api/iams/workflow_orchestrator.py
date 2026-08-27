import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from concurrent.futures import ThreadPoolExecutor, as_completed
from base_agent import UserInputs
from agents import (
    InputValidationAgent, LoadExtractionAgent, GeospatialAgent,
    PVDataAgent, ScenarioRouterAgent, ScenarioCalculationAgent,
    AIAnalysisAgent, FinancialAgent, ReportingAgent, SensitivityAgent,
    MonteCarloAgent, FeasibilityAgent,
)


class PVESSWorkflowOrchestrator:
    def __init__(self):
        self.input_agent      = InputValidationAgent()
        self.load_agent       = LoadExtractionAgent()
        self.geospatial_agent = GeospatialAgent()
        self.pv_agent         = PVDataAgent()
        self.router_agent     = ScenarioRouterAgent()
        self.scenario_agent   = ScenarioCalculationAgent()
        self.ai_agent         = AIAnalysisAgent()
        self.financial_agent  = FinancialAgent()
        self.reporting_agent  = ReportingAgent()
        self.sensitivity_agent = SensitivityAgent()
        self.montecarlo_agent = MonteCarloAgent()
        self.feasibility_agent = FeasibilityAgent()

    def run_full_workflow(self, raw_user_inputs: dict, progress_callback=None) -> dict:
        """
        Run the full end-to-end agentic workflow.

        progress_callback(agent_name: str, status: str, detail: str)
            status: "running" | "done" | "error"
        """
        def cb(name, status, detail=""):
            if progress_callback:
                progress_callback(name, status, detail)

        try:
            # Step 1: Input Validation
            cb("Input Validation", "running")
            validated_inputs = self.input_agent.run(raw_user_inputs)
            cb("Input Validation", "done", validated_inputs.project_address)

            # Step 2: Load Extraction + Geospatial in parallel
            cb("Load Extraction", "running")
            cb("Geospatial", "running")

            load_data = None
            geospatial_data = None
            errors = {}

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_load = executor.submit(self.load_agent.run, validated_inputs)
                future_geo  = executor.submit(self.geospatial_agent.run, validated_inputs)

                for future in as_completed([future_load, future_geo]):
                    if future is future_load:
                        try:
                            load_data = future.result()
                            cb("Load Extraction", "done", f"Max {load_data.max_hourly_load} kW")
                        except Exception as e:
                            errors["Load Extraction"] = str(e)
                            cb("Load Extraction", "error", str(e))
                    else:
                        try:
                            geospatial_data = future.result()
                            location_detail = geospatial_data.formatted_address or (
                                f"{geospatial_data.latitude:.2f}°, {geospatial_data.longitude:.2f}°"
                            )
                            cb("Geospatial", "done", location_detail)
                        except Exception as e:
                            errors["Geospatial"] = str(e)
                            cb("Geospatial", "error", str(e))

            if errors:
                raise ValueError(f"Parallel step failed: {errors}")

            # Step 3: PV Data
            cb("PV Data", "running")
            pv_system_data = self.pv_agent.run(validated_inputs, geospatial_data, load_data)
            cb("PV Data", "done", f"Total {pv_system_data.total_daily_pv} kWh/day")

            # Step 4: Scenario Routing
            cb("Scenario Router", "running")
            scenario_name = self.router_agent.run(validated_inputs)
            cb("Scenario Router", "done", scenario_name)

            # Step 5: Scenario Calculation
            cb("Scenario Calculation", "running")
            scenario_result = self.scenario_agent.run(scenario_name, validated_inputs, load_data, pv_system_data)
            cb("Scenario Calculation", "done", f"PV {scenario_result.pv_capacity_est} kWp | ESS {scenario_result.ess_capacity_est} kWh")

            # Step 6: Seasonal risk detection
            seasonal_risk = self.sensitivity_agent.detect_seasonal_risk(pv_system_data)

            # Step 7: AI Analysis
            cb("AI Analysis", "running")
            ai_analysis = self.ai_agent.run(scenario_result, seasonal_risk=seasonal_risk)
            cb("AI Analysis", "done", ai_analysis.summary)

            # Step 8: Financial Calculation
            cb("Financial", "running")
            financial_result = self.financial_agent.run(validated_inputs, scenario_result)
            cb("Financial", "done", f"IRR {financial_result.irr_percent}%")

            # Step 9: Sensitivity Analysis
            cb("Sensitivity", "running")
            sensitivity_result = self.sensitivity_agent.run(validated_inputs, scenario_result, pv_system_data)
            cb("Sensitivity", "done", f"Base IRR {sensitivity_result.base_irr}%")

            # Step 9.5: Monte Carlo Risk Analysis
            cb("Monte Carlo", "running")
            montecarlo_result = self.montecarlo_agent.run(validated_inputs, scenario_result)
            cb("Monte Carlo", "done", f"P(IRR>WACC) {montecarlo_result.prob_irr_above_wacc:.1%}")

            # Step 10: Feasibility Assessment
            cb("Feasibility", "running")
            feasibility_result = self.feasibility_agent.run(
                scenario_result,
                financial_result,
                sensitivity_result,
            )
            cb("Feasibility", "done", feasibility_result.status)

            # Step 11: Report Generation
            cb("Report", "running")
            markdown_report, summary_df = self.reporting_agent.run(
                validated_inputs, load_data, geospatial_data,
                pv_system_data, scenario_result, ai_analysis, financial_result,
                montecarlo_result
            )
            cb("Report", "done", "Report ready")

            return {
                "success": True,
                "validated_inputs": validated_inputs,
                "load_data": load_data,
                "geospatial_data": geospatial_data,
                "pv_system_data": pv_system_data,
                "scenario_name": scenario_name,
                "scenario_result": scenario_result,
                "ai_analysis": ai_analysis,
                "financial_result": financial_result,
                "sensitivity_result": sensitivity_result,
                "montecarlo_result": montecarlo_result,
                "feasibility_result": feasibility_result,
                "markdown_report": markdown_report,
                "summary_df": summary_df
            }

        except Exception as e:
            print(f"[ERROR] Workflow failed: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }

    # ------------------------------------------------------------------
    # Multi-scenario comparison: run all 4 ESS modes with same PV/load data
    # ------------------------------------------------------------------
    def run_multi_scenario_comparison(self, base_result: dict) -> dict:
        """
        Re-uses already-computed PV, load, and geospatial data from a completed
        run_full_workflow result to run all 4 ESS modes and compare.
        Returns a dict compatible with MultiScenarioComparison schema.
        """
        from base_agent import MultiScenarioComparison
        if not base_result.get("success"):
            return {"success": False, "error_message": "Base workflow must succeed first"}

        validated_inputs  = base_result["validated_inputs"]
        load_data         = base_result["load_data"]
        pv_system_data    = base_result["pv_system_data"]

        modes = [
            "Off-grid sensitive type",
            "Off-grid non-sensitive type",
            "Peak-shaving / demand-charge",
        ]
        capacity_flag = validated_inputs.fixed_capacity is not None and validated_inputs.fixed_capacity > 0

        results = []
        for mode in modes:
            try:
                tmp_inputs = validated_inputs.model_copy(update={"ess_mode": mode})
                sname = self.router_agent.run(tmp_inputs)
                sc = self.scenario_agent.run(sname, tmp_inputs, load_data, pv_system_data)
                fin = self.financial_agent.run(tmp_inputs, sc)
                results.append((mode, sc, fin))
            except Exception as e:
                print(f"[WARN] Multi-scenario {mode} failed: {e}")

        from base_agent import MultiScenarioComparison
        comp = MultiScenarioComparison(
            scenarios      =[r[0] for r in results],
            pv_capacities  =[r[1].pv_capacity_est for r in results],
            ess_capacities =[r[1].ess_capacity_est for r in results],
            coverage_rates =[round(r[1].load_coverage_rate * 100, 1) for r in results],
            irr_percents   =[r[2].irr_percent for r in results],
            initial_costs  =[r[2].initial_cost_10k for r in results],
            co2_savings    =[r[2].annual_co2_avoided_tons for r in results],
        )
        return {"success": True, "comparison": comp}


if __name__ == "__main__":
    test_inputs = {
        "project_address": "Shanghai, China",
        "load_information": "11 PM to 2 AM 700kW, 9 AM to 12 PM 1200kW, 3 PM 1000kW, 5:00 to 7:00 1500kW",
        "ess_mode": "Off-grid sensitive type",
        "fixed_capacity": 1500,
        "install_type": "roof",
        "grid_price": 0.9,
        "initial_pv_capacity": 1000
    }

    def print_cb(name, status, detail):
        icon = {"running": "🔄", "done": "✅", "error": "❌"}.get(status, "⚪")
        print(f"  {icon} [{name}] {detail}")

    orchestrator = PVESSWorkflowOrchestrator()
    result = orchestrator.run_full_workflow(test_inputs, progress_callback=print_cb)

    if result["success"]:
        print("\nWorkflow completed successfully!")
        print(result["markdown_report"])
    else:
        print(f"\nWorkflow failed: {result['error_message']}")
