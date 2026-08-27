from base_agent import BaseAgent, UserInputs

class InputValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Input Validation Agent")

    def run(self, raw_inputs: dict) -> UserInputs:
        """Validate and sanitize raw user inputs"""
        self.log("Starting input validation")

        # Sanitize fixed capacity: treat 0/empty as None (proposed capacity)
        if raw_inputs.get("fixed_capacity") in [0, None, ""]:
            raw_inputs["fixed_capacity"] = None

        # Validate against schema
        validated_inputs = self.validate_schema(raw_inputs, UserInputs)
        self.log(f"Validated inputs for project: {validated_inputs.project_address}")
        return validated_inputs

# Re-export all agents so orchestrator can import from one place
from load_data_agent import LoadExtractionAgent
from geo_agent import GeospatialAgent
from pv_data_agent import PVDataAgent
from scenario_agent import ScenarioRouterAgent
from scenario_culc_agent import ScenarioCalculationAgent
from financial_culc_agent import FinancialAgent
from reporting_agent import ReportingAgent
from ai_analysis_agent import AIAnalysisAgent
from sensitivity_agent import SensitivityAgent
from montecarlo_agent import MonteCarloAgent
from feasibility_agent import FeasibilityAgent
