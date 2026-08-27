from base_agent import BaseAgent, ScenarioResult, UserInputs, LoadData, PVSystemData
import numpy as np

# Annual PV panel degradation rate (0.5 %/year; used for ESS sizing horizon)
_PV_DEG_RATE = 0.005

class ScenarioCalculationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Scenario Calculation Agent")
        self.scenario_functions = {
            "Off-grid sensitive + Fixed capacity":        self._fixed_sensitive,
            "Off-grid sensitive + Proposed capacity":     self._planned_sensitive,
            "Off-grid non-sensitive + Fixed capacity":    self._fixed_non_sensitive,
            "Off-grid non-sensitive + Proposed capacity": self._planned_non_sensitive,
            "Grid-tie + Fixed capacity":                  self._grid_tie_fixed,
            "Grid-tie + Proposed capacity":               self._grid_tie_planned,
            "Peak-shaving + Fixed capacity":              self._peak_shaving_fixed,
            "Peak-shaving + Proposed capacity":           self._peak_shaving_planned,
        }

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _base_metrics(self, pv_capacity: float, init_cap: float,
                      hourly_pv: np.ndarray, hourly_load: np.ndarray):
        """Scale PV by capacity ratio and return basic energy metrics."""
        scale = pv_capacity / init_cap
        scaled_pv = hourly_pv * scale
        surplus = np.maximum(scaled_pv - hourly_load, 0)
        deficit = np.maximum(hourly_load - scaled_pv, 0)
        pv_total = float(scaled_pv.sum())
        surplus_total = float(surplus.sum())
        curt_rate = surplus_total / pv_total if pv_total > 0 else 0.0
        load_coverage = min(pv_total, float(hourly_load.sum())) / float(hourly_load.sum()) \
            if hourly_load.sum() > 0 else 0.0
        return scaled_pv, surplus, deficit, pv_total, surplus_total, curt_rate, load_coverage

    def _ess_size_sensitive(self, load: LoadData, surplus_total: float,
                            autonomy_days: float) -> float:
        """
        Off-grid sensitive: ESS must cover:
          - at minimum 2× max hourly load (peak power buffer)
          - enough energy for `autonomy_days` of full daily load (cloudy backup)
          - plus absorb surplus generation
        Degradation headroom: size for end-of-life (after 25 yr × 0.5% PV drop → ~12%
        battery capacity fade assumed; add 15% margin).
        """
        min_power_buffer = load.max_hourly_load * 2
        energy_autonomy = load.total_daily_load * autonomy_days
        energy_surplus = surplus_total * 0.8
        raw = max(min_power_buffer, energy_autonomy, energy_surplus)
        raw *= 1.15   # 15% degradation / DoD margin
        return max(100.0, float(int(round(raw / 100)) * 100))

    def _ess_size_non_sensitive(self, surplus_total: float, curt_rate: float,
                                autonomy_days: float) -> float:
        """Off-grid non-sensitive: ESS absorbs surplus; optional small autonomy buffer."""
        if curt_rate < 0.05:
            return 0.0
        raw = surplus_total * 0.7 + (surplus_total * 0.3 * min(autonomy_days / 2, 1))
        return max(100.0, float(int(round(raw / 100)) * 100))

    # ------------------------------------------------------------------
    # Off-grid sensitive
    # ------------------------------------------------------------------
    def _fixed_sensitive(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        pv_capacity = inputs.fixed_capacity if (inputs.fixed_capacity or 0) > 0 else inputs.initial_pv_capacity
        _, surplus, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
            pv_capacity, inputs.initial_pv_capacity,
            np.array(pv.hourly_pv_avg), np.array(load.hourly_load)
        )
        ess_capacity = self._ess_size_sensitive(load, surplus_total, inputs.autonomy_days)
        return dict(pv_capacity_est=pv_capacity, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=curt_rate, pv_utilization_rate=1 - curt_rate,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days)

    def _planned_sensitive(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        init_cap = inputs.initial_pv_capacity
        best_cap, best_score, best_m = init_cap, -1e9, None
        for cap in range(max(100, int(init_cap * 0.5)), max(100, int(init_cap * 2.0)) + 1, 100):
            _, _, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
                cap, init_cap, np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
            score = load_coverage - 0.6 * curt_rate
            if score > best_score:
                best_score, best_cap = score, cap
                best_m = (pv_total, surplus_total, curt_rate, load_coverage)
            if load_coverage >= 0.90 and curt_rate <= 0.40:
                break
        pv_total, surplus_total, curt_rate, load_coverage = best_m
        ess_capacity = self._ess_size_sensitive(load, surplus_total, inputs.autonomy_days)
        return dict(pv_capacity_est=best_cap, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=curt_rate, pv_utilization_rate=1 - curt_rate,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days)

    # ------------------------------------------------------------------
    # Off-grid non-sensitive
    # ------------------------------------------------------------------
    def _fixed_non_sensitive(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        pv_capacity = inputs.fixed_capacity if (inputs.fixed_capacity or 0) > 0 else inputs.initial_pv_capacity
        _, _, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
            pv_capacity, inputs.initial_pv_capacity,
            np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
        ess_capacity = self._ess_size_non_sensitive(surplus_total, curt_rate, inputs.autonomy_days)
        return dict(pv_capacity_est=pv_capacity, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=curt_rate, pv_utilization_rate=1 - curt_rate,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days)

    def _planned_non_sensitive(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        init_cap = inputs.initial_pv_capacity
        best_cap, best_curt = 100, 1.0
        for cap in range(100, 10001, 100):
            _, _, _, pv_total, surplus_total, curt_rate, _ = self._base_metrics(
                cap, init_cap, np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
            if 0.05 <= curt_rate <= 0.3:
                best_cap, best_curt = cap, curt_rate
                break
            elif curt_rate < 0.05:
                best_cap, best_curt = cap, curt_rate
        _, _, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
            best_cap, init_cap, np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
        ess_capacity = self._ess_size_non_sensitive(surplus_total, curt_rate, inputs.autonomy_days)
        return dict(pv_capacity_est=best_cap, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=curt_rate, pv_utilization_rate=1 - curt_rate,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days)

    # ------------------------------------------------------------------
    # Grid-tie / self-consumption
    # Grid sells surplus to grid; ESS sized to shift self-consumption
    # ------------------------------------------------------------------
    def _grid_tie_fixed(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        pv_capacity = inputs.fixed_capacity if (inputs.fixed_capacity or 0) > 0 else inputs.initial_pv_capacity
        _, surplus, deficit, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
            pv_capacity, inputs.initial_pv_capacity,
            np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
        # ESS sized to shift ~60% of daily surplus into evening deficit hours
        ess_capacity = float(int(round(surplus_total * 0.6 / 100)) * 100)
        ess_capacity = max(100.0, ess_capacity) if surplus_total > 0 else 0.0
        grid_export = surplus_total  # daily export kWh (before ESS absorption)
        return dict(pv_capacity_est=pv_capacity, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=0.0,  # grid absorbs all surplus
                    pv_utilization_rate=1.0, load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days, grid_export_kwh=grid_export)

    def _grid_tie_planned(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        init_cap = inputs.initial_pv_capacity
        # Optimize: maximize self-consumption (minimize export fraction)
        best_cap, best_score, best_m = init_cap, -1e9, None
        for cap in range(max(100, int(init_cap * 0.3)), max(100, int(init_cap * 2.0)) + 1, 100):
            _, surplus, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
                cap, init_cap, np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
            self_ratio = (pv_total - surplus_total) / pv_total if pv_total > 0 else 0
            score = self_ratio * 0.7 + load_coverage * 0.3
            if score > best_score:
                best_score, best_cap, best_m = score, cap, (pv_total, surplus_total, load_coverage)
        pv_total, surplus_total, load_coverage = best_m
        ess_capacity = float(int(round(surplus_total * 0.6 / 100)) * 100)
        ess_capacity = max(100.0, ess_capacity) if surplus_total > 0 else 0.0
        return dict(pv_capacity_est=best_cap, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=0.0, pv_utilization_rate=1.0,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days, grid_export_kwh=surplus_total)

    # ------------------------------------------------------------------
    # Peak-shaving / demand-charge reduction
    # Battery charges from PV/grid at off-peak, discharges at peak
    # ------------------------------------------------------------------
    def _peak_shaving_fixed(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        pv_capacity = inputs.fixed_capacity if (inputs.fixed_capacity or 0) > 0 else inputs.initial_pv_capacity
        _, _, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
            pv_capacity, inputs.initial_pv_capacity,
            np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
        # Peak demand = max hourly load; ESS covers 2h of peak
        peak_shaved_kwh = load.max_hourly_load * 2
        ess_capacity = float(int(round(peak_shaved_kwh * 1.25 / 100)) * 100)
        ess_capacity = max(100.0, ess_capacity)
        return dict(pv_capacity_est=pv_capacity, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=curt_rate, pv_utilization_rate=1 - curt_rate,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days, peak_shaved_kwh=peak_shaved_kwh)

    def _peak_shaving_planned(self, inputs: UserInputs, load: LoadData, pv: PVSystemData) -> dict:
        init_cap = inputs.initial_pv_capacity
        # Choose PV to cover ~70% of daytime load; battery covers peak demand hours
        best_cap, best_m = init_cap, None
        target_cov = 0.70
        for cap in range(100, max(100, int(init_cap * 2.0)) + 1, 100):
            _, _, _, pv_total, surplus_total, curt_rate, load_coverage = self._base_metrics(
                cap, init_cap, np.array(pv.hourly_pv_avg), np.array(load.hourly_load))
            if load_coverage >= target_cov:
                best_cap = cap
                best_m = (pv_total, surplus_total, curt_rate, load_coverage)
                break
            best_cap = cap
            best_m = (pv_total, surplus_total, curt_rate, load_coverage)
        pv_total, surplus_total, curt_rate, load_coverage = best_m
        peak_shaved_kwh = load.max_hourly_load * 2
        ess_capacity = float(int(round(peak_shaved_kwh * 1.25 / 100)) * 100)
        ess_capacity = max(100.0, ess_capacity)
        return dict(pv_capacity_est=best_cap, ess_capacity_est=ess_capacity,
                    pv_total=pv_total, surplus_total=surplus_total,
                    curtailment_rate=curt_rate, pv_utilization_rate=1 - curt_rate,
                    load_coverage_rate=load_coverage,
                    ess_match_ratio=surplus_total / ess_capacity if ess_capacity > 0 else None,
                    autonomy_days=inputs.autonomy_days, peak_shaved_kwh=peak_shaved_kwh)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run(self, scenario_name: str, inputs: UserInputs, load_data: LoadData, pv_data: PVSystemData) -> ScenarioResult:
        self.log(f"Starting calculation for scenario: {scenario_name}")
        calc_fn = self.scenario_functions[scenario_name]
        raw = calc_fn(inputs, load_data, pv_data)
        result = self.validate_schema({"scenario_name": scenario_name, **raw}, ScenarioResult)
        self.log(f"Calculation complete: PV {result.pv_capacity_est} kWp | ESS {result.ess_capacity_est} kWh | Coverage {round(result.load_coverage_rate*100,1)}%")
        return result
