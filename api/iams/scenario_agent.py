from base_agent import BaseAgent, UserInputs

class ScenarioRouterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Scenario Router Agent")
        self.scenario_map = {
            ("Off-grid sensitive type",   True):  "Off-grid sensitive + Fixed capacity",
            ("Off-grid sensitive type",   False): "Off-grid sensitive + Proposed capacity",
            ("Off-grid non-sensitive type", True):  "Off-grid non-sensitive + Fixed capacity",
            ("Off-grid non-sensitive type", False): "Off-grid non-sensitive + Proposed capacity",
            ("Grid-tie / self-consumption",    True):  "Grid-tie + Fixed capacity",
            ("Grid-tie / self-consumption",    False): "Grid-tie + Proposed capacity",
            ("Peak-shaving / demand-charge", True):  "Peak-shaving + Fixed capacity",
            ("Peak-shaving / demand-charge", False): "Peak-shaving + Proposed capacity",
        }

    def run(self, validated_inputs: UserInputs) -> str:
        self.log("Starting scenario routing")
        has_fixed = validated_inputs.fixed_capacity is not None and validated_inputs.fixed_capacity > 0
        key = (validated_inputs.ess_mode, has_fixed)
        scenario_name = self.scenario_map[key]
        self.log(f"Routed to scenario: {scenario_name}")
        return scenario_name
