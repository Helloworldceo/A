from base_agent import BaseAgent
from base_agent import UserInputs, GeospatialData, PVSystemData, LoadData
import requests
import time
import os

class PVDataAgent(BaseAgent):
    def __init__(self):
        super().__init__("PV Data Agent")
        self.solar_api_base_url = os.getenv("GLOBAL_SOLAR_ATLAS_BASE_URL")
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://globalsolaratlas.info",
            "referer": "https://globalsolaratlas.info/",
            "user-agent": "PV-ESS-Intelligent-Assistant/1.0"
        }
        self.install_type_map = {
            "roof": "rooftopLargeFlat",
            "ground": "groundFixed",
            "hydro": "hydroMountedLargeScale"
        }

    def _fetch_all_pv_data(self, geospatial: GeospatialData, pv_capacity: float, install_type: str) -> dict:
        """Fetch all available fields from Global Solar Atlas (annual, monthly, monthly-hourly)."""
        # Estimate timezone offset from longitude (seconds)
        gmt_offset_sec = int(round(geospatial.longitude / 15.0)) * 3600

        for attempt in range(self.max_retries):
            try:
                url = f"{self.solar_api_base_url}/data/pvcalc"
                params = {"loc": f"{geospatial.latitude},{geospatial.longitude}",
                          "gmtOffset": str(gmt_offset_sec)}
                payload = {
                    "type": self.install_type_map[install_type],
                    "systemSize": {"type": "capacity", "value": pv_capacity},
                    "orientation": {"azimuth": geospatial.optimal_azimuth, "tilt": geospatial.optimal_tilt}
                }
                response = requests.post(url, headers=self.headers, params=params,
                                         json=payload, timeout=15)
                response.raise_for_status()
                return response.json()

            except Exception as e:
                self.log(f"PV API attempt {attempt+1} failed: {str(e)}", "WARNING")
                if attempt == self.max_retries - 1:
                    self.log("Falling back to mock PV data", "WARNING")
                    return None
                time.sleep(self.backoff_factor ** attempt)

    def _mock_data(self, pv_capacity: float) -> dict:
        """Realistic mock when API is unreachable (preserves all schema fields)."""
        # Simulate a sunny tropical site ~1400 kWh/kWp/yr
        base_hourly = [0]*6 + [50, 200, 400, 600, 750, 850, 900, 850, 750, 600, 400, 200, 50, 0]*1 + [0]*3
        base_hourly = (base_hourly + [0]*24)[:24]  # ensure 24
        scale = pv_capacity / 1000.0
        mh_pvout = [[round(v * scale, 3) for v in base_hourly] for _ in range(12)]
        mh_gti    = [[round(v * 1.1, 3) for v in base_hourly] for _ in range(12)]
        monthly_total = [round(sum(row) * 30, 1) for row in mh_pvout]
        monthly_spec  = [round(t / pv_capacity, 1) for t in monthly_total]
        monthly_gti   = [round(sum(row) * 30 / pv_capacity * 1.1, 1) for row in mh_pvout]
        monthly_dni   = [round(g * 0.7, 1) for g in monthly_gti]
        return {
            "annual": {"data": {
                "PVOUT_specific": round(sum(monthly_spec), 1),
                "PVOUT_total":    round(sum(monthly_total) * 1000, 1),
                "DNI":            round(sum(monthly_dni), 1),
                "GTI":            round(sum(monthly_gti), 1),
            }},
            "monthly": {"data": {
                "PVOUT_total":    [t * 1000 for t in monthly_total],
                "PVOUT_specific": monthly_spec,
                "DNI":            monthly_dni,
                "GTI":            monthly_gti,
            }},
            "monthly-hourly": {"data": {
                "PVOUT_total":    [[v * 1000 for v in row] for row in mh_pvout],
                "GTI":            mh_gti,
                "PVOUT_specific": [[round(v / pv_capacity, 4) for v in row] for row in
                                   [[v * 1000 for v in r] for r in mh_pvout]],
                "DNI":            [[round(v * 0.7, 3) for v in row] for row in mh_gti],
            }},
        }

    def run(self, validated_inputs: UserInputs, geospatial: GeospatialData, load_data: LoadData) -> PVSystemData:
        """Fetch all GSA fields and compute derived metrics."""
        self.log("Starting PV data processing")

        raw = self._fetch_all_pv_data(geospatial, validated_inputs.initial_pv_capacity,
                                      validated_inputs.install_type)
        if raw is None:
            raw = self._mock_data(validated_inputs.initial_pv_capacity)

        # --- Annual (values already in kWh from GSA) ---
        ann = raw["annual"]["data"]
        annual_pvout_specific = round(ann["PVOUT_specific"], 3)   # kWh/kWp
        annual_pvout_total    = round(ann["PVOUT_total"], 3)       # kWh
        annual_dni            = round(ann["DNI"], 3)               # kWh/m²
        annual_gti            = round(ann["GTI"], 3)               # kWh/m²

        # --- Monthly (values already in kWh from GSA) ---
        mon = raw["monthly"]["data"]
        monthly_pvout_total  = [round(v, 3) for v in mon["PVOUT_total"]]    # kWh
        monthly_pvout_spec   = [round(v, 3) for v in mon["PVOUT_specific"]] # kWh/kWp
        monthly_dni          = [round(v, 3) for v in mon["DNI"]]            # kWh/m²
        monthly_gti          = [round(v, 3) for v in mon["GTI"]]            # kWh/m²

        # --- Monthly-hourly matrices (values in Wh from GSA → convert to kWh) ---
        mh = raw["monthly-hourly"]["data"]
        matrix_pvout = [[round(v / 1000, 4) for v in row] for row in mh["PVOUT_total"]]
        matrix_gti   = [[round(v, 4) for v in row] for row in mh["GTI"]]

        # --- 24-hour averages across 12 months ---
        hourly_pv_avg  = [round(sum(month[h] for month in matrix_pvout) / 12, 4) for h in range(24)]
        hourly_gti_avg = [round(sum(month[h] for month in matrix_gti)   / 12, 4) for h in range(24)]

        total_daily_pv = round(sum(hourly_pv_avg), 3)

        hourly_pv_surplus  = [round(max(pv - load, 0), 4)
                               for pv, load in zip(hourly_pv_avg, load_data.hourly_load)]
        total_daily_surplus = round(sum(hourly_pv_surplus), 3)
        curtailment_rate    = round(total_daily_surplus / total_daily_pv, 4) if total_daily_pv > 0 else 0.0

        pv_system_data = self.validate_schema({
            # 24-hour profiles
            "hourly_pv_avg":         hourly_pv_avg,
            "hourly_gti_avg":        hourly_gti_avg,
            "total_daily_pv":        total_daily_pv,
            "hourly_pv_surplus":     hourly_pv_surplus,
            "total_daily_surplus":   total_daily_surplus,
            "curtailment_rate":      curtailment_rate,
            # Annual
            "annual_pvout_specific": annual_pvout_specific,
            "annual_pvout_total_kwh": annual_pvout_total,
            "annual_dni":            annual_dni,
            "annual_gti":            annual_gti,
            # Monthly
            "monthly_pvout_total_kwh": monthly_pvout_total,
            "monthly_pvout_specific":  monthly_pvout_spec,
            "monthly_dni":             monthly_dni,
            "monthly_gti":             monthly_gti,
            # Full matrices
            "matrix_pvout_total":    matrix_pvout,
            "matrix_gti":            matrix_gti,
        }, PVSystemData)

        self.log(
            f"PV Annual: {annual_pvout_total:.1f} kWh | "
            f"Specific Yield: {annual_pvout_specific:.1f} kWh/kWp | "
            f"GTI: {annual_gti:.1f} kWh/m² | DNI: {annual_dni:.1f} kWh/m²"
        )
        return pv_system_data

