"""
montecarlo_agent.py
────────────────────
Probabilistic risk assessment via Monte Carlo simulation.

Extends the deterministic point-estimate financial model (FinancialAgent)
into a distribution of outcomes by re-running it many times against
independently sampled solar-resource and grid-price scale factors. Does
not duplicate any financial math — every draw calls the existing,
already-verified FinancialAgent.run().

Reproducibility: uses a fixed-seed NumPy Generator, so identical
(inputs, scenario) pairs always produce bit-identical sample arrays and
summary statistics across repeated runs — consistent with the
determinism protocol used elsewhere in this project (reproducibility_cli.py).
"""
from base_agent import BaseAgent, MonteCarloResult, UserInputs, ScenarioResult
from financial_culc_agent import FinancialAgent
import numpy as np


class MonteCarloAgent(BaseAgent):
    # Uncertain-parameter distributions (multiplicative scale factors, mean 1.0):
    #   solar resource interannual variability: Normal(1.0, 0.05)
    #     -- consistent with literature-reported ~2.5-10% interannual
    #        coefficient-of-variation for regional solar resource.
    #   grid tariff / price volatility: Normal(1.0, 0.15)
    #     -- consistent with the +-20% deterministic price-sensitivity
    #        bound already used elsewhere in this thesis (SensitivityAgent).
    # Sampled independently: no correlation between solar and price shocks
    # is modeled (stated simplifying assumption; see thesis Ch3/Ch6).
    SOLAR_STD = 0.05
    PRICE_STD = 0.15

    def __init__(self, n_simulations: int = 2000, seed: int = 42):
        super().__init__("Monte Carlo Risk Agent")
        self.n_simulations = n_simulations
        self.seed = seed
        self._fin = FinancialAgent()

    def run(self, inputs: UserInputs, scenario: ScenarioResult) -> MonteCarloResult:
        self.log(f"Starting Monte Carlo risk analysis for: {scenario.scenario_name} "
                  f"(N={self.n_simulations}, seed={self.seed})")

        rng = np.random.default_rng(self.seed)
        solar_scales = rng.normal(1.0, self.SOLAR_STD, self.n_simulations)
        price_scales = rng.normal(1.0, self.PRICE_STD, self.n_simulations)

        irr_samples = []
        npv_samples = []
        for solar_scale, price_scale in zip(solar_scales, price_scales):
            solar_scale = max(solar_scale, 0.0)   # generation cannot go negative
            price_scale = max(price_scale, 0.0)   # price cannot go negative

            scaled_scenario = scenario.model_copy(update={
                "pv_total": scenario.pv_total * solar_scale,
                "surplus_total": scenario.surplus_total * solar_scale,
            })
            scaled_inputs = inputs.model_copy(update={
                "grid_price": inputs.grid_price * price_scale
            })

            fin = self._fin.run(scaled_inputs, scaled_scenario)
            npv_samples.append(fin.npv_10k if fin.npv_10k is not None else float("nan"))
            if fin.irr_percent is not None:
                irr_samples.append(fin.irr_percent)

        wacc_percent = self._fin.constants["discount_rate"] * 100
        npv_arr = np.array(npv_samples, dtype=float)
        npv_arr = npv_arr[~np.isnan(npv_arr)]

        if irr_samples:
            irr_arr = np.array(irr_samples, dtype=float)
            irr_mean = float(np.mean(irr_arr))
            irr_std = float(np.std(irr_arr))
            irr_p10 = float(np.percentile(irr_arr, 10))
            irr_p50 = float(np.percentile(irr_arr, 50))
            irr_p90 = float(np.percentile(irr_arr, 90))
            prob_irr_above_wacc = float(np.mean(irr_arr > wacc_percent))
        else:
            irr_mean = irr_std = irr_p10 = irr_p50 = irr_p90 = None
            prob_irr_above_wacc = 0.0

        result = self.validate_schema({
            "scenario_name": scenario.scenario_name,
            "n_simulations": self.n_simulations,
            "seed": self.seed,
            "irr_mean": round(irr_mean, 4) if irr_mean is not None else None,
            "irr_std": round(irr_std, 4) if irr_std is not None else None,
            "irr_p10": round(irr_p10, 4) if irr_p10 is not None else None,
            "irr_p50": round(irr_p50, 4) if irr_p50 is not None else None,
            "irr_p90": round(irr_p90, 4) if irr_p90 is not None else None,
            "npv_mean": round(float(np.mean(npv_arr)), 4) if len(npv_arr) else 0.0,
            "npv_p5_var": round(float(np.percentile(npv_arr, 5)), 4) if len(npv_arr) else 0.0,
            "prob_irr_above_wacc": round(prob_irr_above_wacc, 4),
            "prob_npv_positive": round(float(np.mean(npv_arr > 0)), 4) if len(npv_arr) else 0.0,
            "irr_samples": [round(v, 4) for v in irr_samples],
        }, MonteCarloResult)

        self.log(f"Monte Carlo complete: IRR P10/P50/P90 = "
                 f"{result.irr_p10}/{result.irr_p50}/{result.irr_p90}% | "
                 f"P(IRR>WACC={wacc_percent:.1f}%) = {result.prob_irr_above_wacc:.2%} | "
                 f"VaR(5%) NPV = {result.npv_p5_var} 万元")
        return result
