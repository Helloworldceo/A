from base_agent import BaseAgent, AIAnalysisResult, ScenarioResult
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os

# System prompts verbatim from IAMS.01.yml — one per scenario
_PROMPTS = {
    "Off-grid sensitive + Proposed capacity": """You are an expert in photovoltaic system design analysis.
Based on the following calculation results, evaluate the system configuration reasonableness and generate a structured JSON output.

---

Input data:

- Recommended PV capacity (pv_capacity_est): {pv_capacity_est}
- Total PV generation (pv_total): {pv_total}
- Total PV surplus (pv_surplus_total): {surplus_total}
- Curtailment rate (curt_rate): {curtailment_rate}
- PV utilization rate (pv_util_rate): {pv_utilization_rate}
- Load coverage (load_coverage): {load_coverage_rate}
- Recommended ESS capacity (ess_capacity_est): {ess_capacity_est}
- ESS match (ess_match): {ess_match_ratio}

---

Judgment logic:

- In off-grid sensitive scenarios, the system **must have ESS configured**; if ess_capacity_est = 0, indicate "configuration insufficient".
- If curt_rate < 0.1 → ESS capacity is relatively large, surplus exists; ESS can be moderately reduced.
- If curt_rate between 0.1~0.4 → ESS capacity is well matched.
- If curt_rate > 0.4 → PV capacity too large or ESS too small.
- If load_coverage < 0.9 → PV capacity too small, daytime cannot meet load.
- If load_coverage > 1.0 → abnormal value; likely a calculation issue.
- If ess_match > 1.2 → ESS capacity too small; should increase ESS.
- If ess_match < 0.5 → ESS capacity too large; can moderately reduce ESS.

---

Output format (JSON):

{{
  "summary": "string, brief conclusion (e.g., 'High PV utilization, ESS configuration reasonable')",
  "conclusion": "string, full analysis describing PV capacity and ESS configuration reasonableness and potential improvements",
  "report": "string, Markdown format PV+ESS analysis report with real line breaks and formatting"
}}""",

    "Off-grid sensitive + Fixed capacity": """You are an expert in photovoltaic system design and energy storage analysis.
Please evaluate the configuration reasonableness of an off-grid sensitive system based on the following input data and generate a structured JSON output.

---

Input data:

- Fixed PV capacity (pv_capacity_est): {pv_capacity_est}
- Total PV generation (pv_total): {pv_total}
- Total PV surplus (pv_surplus_total): {surplus_total}
- Curtailment rate (curt_rate): {curtailment_rate}
- PV utilization rate (pv_util_rate): {pv_utilization_rate}
- Load coverage (load_coverage): {load_coverage_rate}
- Recommended ESS capacity (ess_capacity_est): {ess_capacity_est}
- ESS match (ess_match): {ess_match_ratio}

---

Judgment logic:

- Off-grid sensitive systems must have ESS configured (ess_capacity_est > 0)
- If ess_capacity_est < 2 hours average load → ESS insufficient
- If curt_rate > 0.5 → PV capacity too large
- If pv_util_rate < 0.5 → PV utilization rate too low
- If load_coverage < 0.8 → Power supply guarantee insufficient
- If ess_match > 1.2 → ESS too small; if ess_match < 0.5 → ESS too large

---

Output format (JSON):

{{
  "summary": "string, brief conclusion (e.g., 'System configuration reasonable' or 'ESS slightly small')",
  "conclusion": "string, full analysis in English describing PV and ESS matching",
  "report": "string, Markdown format report with real line breaks, no escape characters"
}}""",

    "Off-grid non-sensitive + Fixed capacity": """You are a photovoltaic system design and off-grid energy analysis expert.
Based on the following input data, analyze the system configuration reasonableness and generate a structured JSON output.

---

Input data:

* Fixed PV capacity (pv_capacity_est): {pv_capacity_est}
* Total PV generation (pv_total): {pv_total}
* Total PV surplus (pv_surplus_total): {surplus_total}
* Curtailment rate (curt_rate): {curtailment_rate}
* Load coverage (load_coverage): {load_coverage_rate}
* PV utilization rate (pv_util_rate): {pv_utilization_rate}
* Recommended ESS capacity (ess_capacity_est): {ess_capacity_est}
* ESS match (ess_match): {ess_match_ratio}

---

Analysis logic:

1. Fixed capacity characteristics
   * PV capacity is fixed and cannot be increased; only ESS configuration can be optimized.

2. Judgment logic
   * If curt_rate < 0.05 → PV utilization is high, no ESS required;
   * If curt_rate between 0.05~0.5 → ESS configuration reasonable;
   * If curt_rate > 0.5 → PV capacity may be too large;
   * If load_coverage < 0.7 → PV capacity too small;
   * If load_coverage > 1.0 → abnormal;
   * If ess_match > 1.2 → ESS capacity too small;
   * If ess_match < 0.5 → ESS capacity too large;
   * If ess_capacity_est = 0 and curt_rate < 0.05 → acceptable under off-grid non-sensitive conditions.

---

Output format (JSON):

{{
  "summary": "string, brief conclusion (e.g., 'System configuration reasonable' or 'ESS slightly small')",
  "conclusion": "string, full analysis (in English, describing the overall matching of PV capacity and ESS)",
  "report": "string, Markdown format PV+ESS analysis report with real line breaks, no escape characters"
}}""",

    "Off-grid non-sensitive + Proposed capacity": """You are a photovoltaic system design and off-grid energy analysis expert.
Based on the following input data, analyze the optimized system configuration reasonableness and generate a structured JSON output.

---

Input data:

* Proposed PV capacity (pv_capacity_est): {pv_capacity_est}
* Total PV generation (pv_total): {pv_total}
* Total PV surplus (pv_surplus_total): {surplus_total}
* Curtailment rate (curt_rate): {curtailment_rate}
* Load coverage (load_coverage): {load_coverage_rate}
* PV utilization rate (pv_util_rate): {pv_utilization_rate}
* Recommended ESS capacity (ess_capacity_est): {ess_capacity_est}
* ESS match (ess_match): {ess_match_ratio}

---

Judgment logic:

* If curt_rate < 0.05 → PV utilization is high; no ESS required;
* If curt_rate between 0.05~0.3 → configuration is well optimized for non-sensitive loads;
* If curt_rate > 0.3 → PV capacity may be too large for the load;
* If load_coverage < 0.7 → PV capacity too small;
* If ess_capacity_est = 0 and curt_rate < 0.05 → acceptable for non-sensitive loads;
* If ess_match > 1.2 → ESS too small; if ess_match < 0.5 → ESS too large.

---

Output format (JSON):

{{
  "summary": "string, brief conclusion (e.g., 'Well-optimized configuration' or 'PV slightly oversized')",
  "conclusion": "string, full analysis in English describing whether the proposed capacity is well matched",
  "report": "string, Markdown format PV+ESS analysis report with real line breaks, no escape characters"
}}""",

    "Grid-tie + Fixed capacity": """You are a solar PV grid-tie system analysis expert.
Analyze the self-consumption and grid export performance for a grid-connected PV system.

Input data:
* PV capacity (pv_capacity_est): {pv_capacity_est} kWp
* Daily PV generation (pv_total): {pv_total} kWh
* Daily grid export (surplus_total): {surplus_total} kWh
* Self-consumption ratio: {pv_utilization_rate}
* Load coverage: {load_coverage_rate}
* ESS capacity for shifting (ess_capacity_est): {ess_capacity_est} kWh

Judgment logic:
* Self-consumption ratio > 0.7 → good; if < 0.4 → oversized PV
* Load coverage < 0.5 → PV undersized for daytime demand
* ESS > 0 → shifts surplus to evening peak; increases self-consumption

Output format (JSON):
{{
  "summary": "string, brief grid-tie assessment",
  "conclusion": "string, full analysis of self-consumption, export, and ESS shifting value",
  "report": "string, Markdown format report"
}}""",

    "Grid-tie + Proposed capacity": """You are a solar PV grid-tie system analysis expert.
Analyze the proposed PV system optimized for maximum self-consumption and grid export value.

Input data:
* Proposed PV capacity (pv_capacity_est): {pv_capacity_est} kWp
* Daily PV generation (pv_total): {pv_total} kWh
* Daily grid export (surplus_total): {surplus_total} kWh
* Self-consumption ratio: {pv_utilization_rate}
* Load coverage: {load_coverage_rate}
* ESS for peak-shifting (ess_capacity_est): {ess_capacity_est} kWh

Judgment logic:
* Optimal self-consumption 60–80%: well-sized system
* If self-consumption < 50%: PV oversized, consider reducing capacity
* ESS shifting surplus to evening improves economics

Output format (JSON):
{{
  "summary": "string, brief assessment",
  "conclusion": "string, full analysis",
  "report": "string, Markdown format report"
}}""",

    "Peak-shaving + Fixed capacity": """You are a demand-charge reduction and peak-shaving expert.
Analyze whether the PV+ESS system effectively reduces peak demand charges.

Input data:
* PV capacity (pv_capacity_est): {pv_capacity_est} kWp
* Daily PV generation (pv_total): {pv_total} kWh
* ESS capacity (ess_capacity_est): {ess_capacity_est} kWh
* Peak demand shaved (surplus_total used as proxy): {surplus_total} kWh
* Load coverage: {load_coverage_rate}

Judgment logic:
* ESS sized for 2h of peak demand → effective peak shaving
* PV reduces daytime grid draw; ESS covers evening peak
* If ess_capacity_est < max_load × 2: ESS undersized for peak-shaving

Output format (JSON):
{{
  "summary": "string, peak-shaving effectiveness summary",
  "conclusion": "string, full demand-charge reduction analysis",
  "report": "string, Markdown format report"
}}""",

    "Peak-shaving + Proposed capacity": """You are a demand-charge reduction and peak-shaving expert.
Analyze the proposed PV+ESS system configuration for peak demand reduction.

Input data:
* Proposed PV capacity (pv_capacity_est): {pv_capacity_est} kWp
* Daily PV generation (pv_total): {pv_total} kWh
* ESS capacity (ess_capacity_est): {ess_capacity_est} kWh
* Estimated peak shaved: {surplus_total} kWh
* Load coverage: {load_coverage_rate}

Judgment logic:
* PV reduces daytime consumption; ESS shifts to peak demand hours
* Optimal: cover 70% of daytime load with PV; ESS handles 2h peak
* If load_coverage < 0.5: PV undersized; if > 0.9: potentially oversized

Output format (JSON):
{{
  "summary": "string, peak-shaving assessment",
  "conclusion": "string, full analysis of PV + ESS peak demand reduction",
  "report": "string, Markdown format report"
}}"""
}


class AIAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__("AI Analysis Agent")
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.2,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
            frequency_penalty=0.5,
            presence_penalty=0.5,
            top_p=0.75
        )

    def run(self, scenario_result: ScenarioResult,
            seasonal_risk: str = "") -> AIAnalysisResult:
        """Run LLM analysis for the given scenario result"""
        self.log(f"Starting AI analysis for scenario: {scenario_result.scenario_name}")

        system_prompt = _PROMPTS.get(scenario_result.scenario_name)
        if not system_prompt:
            raise ValueError(f"No prompt found for scenario: {scenario_result.scenario_name}")

        # Format prompt with scenario data
        filled_prompt = system_prompt.format(
            pv_capacity_est=scenario_result.pv_capacity_est,
            pv_total=round(scenario_result.pv_total, 2),
            surplus_total=round(scenario_result.surplus_total, 2),
            curtailment_rate=round(scenario_result.curtailment_rate, 4),
            pv_utilization_rate=round(scenario_result.pv_utilization_rate, 4),
            load_coverage_rate=round(scenario_result.load_coverage_rate, 4),
            ess_capacity_est=scenario_result.ess_capacity_est,
            ess_match_ratio=round(scenario_result.ess_match_ratio, 4) if scenario_result.ess_match_ratio else "N/A"
        )

        prompt_template = [
            SystemMessage(content=filled_prompt),
            HumanMessage(content="Please analyze the configuration and generate the JSON output now.")
        ]

        for attempt in range(self.max_retries):
            try:
                response = self.llm.invoke(prompt_template)
                # Strip markdown code fences if present
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                parsed = json.loads(content.strip())

                ai_result = self.validate_schema({
                    "scenario_name": scenario_result.scenario_name,
                    "summary": parsed["summary"],
                    "conclusion": parsed["conclusion"],
                    "report": parsed["report"],
                    "seasonal_risk": seasonal_risk
                }, AIAnalysisResult)

                self.log(f"AI analysis complete: {ai_result.summary}")
                return ai_result

            except Exception as e:
                self.log(f"AI analysis attempt {attempt+1} failed: {str(e)}", "WARNING")
                if attempt == self.max_retries - 1:
                    self.log("Max retries reached, returning fallback", "ERROR")
                    return AIAnalysisResult(
                        scenario_name=scenario_result.scenario_name,
                        summary="AI analysis unavailable",
                        conclusion="LLM analysis could not be completed. Please review the metrics manually.",
                        report="## AI Analysis\n\n> AI analysis unavailable. Please check your OpenAI API key and try again.",
                        seasonal_risk=seasonal_risk
                    )
