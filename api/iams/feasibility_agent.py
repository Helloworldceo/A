from base_agent import BaseAgent, FeasibilityResult, ScenarioResult, FinancialResult, SensitivityResult


class FeasibilityAgent(BaseAgent):
    def __init__(self):
        super().__init__("Feasibility Agent")

    def run(
        self,
        scenario_result: ScenarioResult,
        financial_result: FinancialResult,
        sensitivity_result: SensitivityResult,
    ) -> FeasibilityResult:
        self.log("Starting feasibility assessment")

        score = 100
        reasons: list[str] = []
        recommendations: list[str] = []

        load_coverage = scenario_result.load_coverage_rate
        curtailment = scenario_result.curtailment_rate
        irr = financial_result.irr_percent
        payback = financial_result.payback_year
        worst_payback = sensitivity_result.payback_year_worst
        worst_irr = min(
            value for value in [
                sensitivity_result.base_irr,
                sensitivity_result.irr_solar_minus10,
                sensitivity_result.irr_price_minus20,
            ] if value is not None
        ) if any(
            value is not None for value in [
                sensitivity_result.base_irr,
                sensitivity_result.irr_solar_minus10,
                sensitivity_result.irr_price_minus20,
            ]
        ) else None

        if load_coverage < 0.7:
            score -= 35
            reasons.append(f"Low load coverage ({load_coverage * 100:.1f}%).")
            recommendations.append("Increase PV capacity or re-balance the selected scenario.")
        elif load_coverage < 0.9:
            score -= 15
            reasons.append(f"Moderate load coverage ({load_coverage * 100:.1f}%).")

        if curtailment > 0.5:
            score -= 20
            reasons.append(f"High curtailment ({curtailment * 100:.1f}%) indicates oversizing or insufficient storage use.")
            recommendations.append("Reduce PV oversizing or increase storage/load utilization.")
        elif curtailment > 0.3:
            score -= 10
            reasons.append(f"Curtailment is elevated ({curtailment * 100:.1f}%).")

        if irr is None or irr < 0:
            score -= 35
            reasons.append("Project IRR is negative or unavailable.")
            recommendations.append("Revisit capital cost and system sizing assumptions.")
        elif irr < 8:
            score -= 15
            reasons.append(f"IRR is modest at {irr:.2f}%.")

        if payback is None or payback > 15:
            score -= 20
            reasons.append("Payback period is too long for a strong investment case.")
        elif payback > 10:
            score -= 10
            reasons.append(f"Payback period is moderate at Year {payback}.")

        if worst_irr is not None and worst_irr < 0:
            score -= 10
            reasons.append("Worst-case sensitivity turns the project unprofitable.")
        elif worst_irr is not None and worst_irr < 5:
            score -= 5
            reasons.append(f"Worst-case IRR falls to {worst_irr:.2f}%.")

        if worst_payback is not None and worst_payback > 15:
            score -= 5
            reasons.append(f"Worst-case payback extends to Year {worst_payback}.")

        score = max(0, min(100, score))

        if score >= 75:
            status = "Feasible"
        elif score >= 50:
            status = "Marginal"
        else:
            status = "Not feasible"

        if not reasons:
            reasons.append("Technical and financial indicators are within acceptable bounds.")
        if not recommendations:
            recommendations.append("Proceed with detailed engineering validation for the selected scenario.")

        result = self.validate_schema({
            "status": status,
            "score": score,
            "summary": f"{status} with score {score}/100 based on coverage, curtailment, IRR, payback, and sensitivity.",
            "reasons": reasons,
            "recommendations": recommendations,
        }, FeasibilityResult)
        self.log(f"Feasibility complete: {result.status} ({result.score}/100)")
        return result