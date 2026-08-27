from base_agent import BaseAgent, GeospatialData, UserInputs
import requests
import time
import os

class GeospatialAgent(BaseAgent):
    def __init__(self):
        super().__init__("Geospatial Agent")
        self.geocode_api_key = os.getenv("OPENCAGE_API_KEY")
        self.geocode_base_url = "https://api.opencagedata.com/geocode/v1/json"

    def _build_display_location(self, address: str, formatted: str, country: str) -> str:
        location = (address or formatted or "").strip()
        country = (country or "").strip()

        if country:
            parts = [part.strip() for part in location.split(",") if part.strip()]
            if not any(part.lower() == country.lower() for part in parts):
                parts.append(country)
            return ", ".join(parts) if parts else country

        if not location:
            return (formatted or "").strip()
        return location

    def _address_to_coordinates(self, address: str) -> tuple[float, float, str, str]:
        """Convert address to lat/lon with resolved location metadata"""
        for attempt in range(self.max_retries):
            try:
                params = {
                    "q": address,
                    "key": self.geocode_api_key,
                    "limit": 1
                }
                response = requests.get(self.geocode_base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data["results"]:
                    raise ValueError("No coordinates found for address")

                result = data["results"][0]
                geometry = result["geometry"]
                components = result.get("components", {})
                country_name = components.get("country", "")
                formatted_address = self._build_display_location(
                    address,
                    result.get("formatted", ""),
                    country_name,
                )
                return geometry["lat"], geometry["lng"], formatted_address, country_name

            except Exception as e:
                self.log(f"Geocoding attempt {attempt+1} failed: {str(e)}", "WARNING")
                if attempt == self.max_retries - 1:
                    self.log("Falling back to default coordinates (Beijing)", "WARNING")
                    fallback_country = "China"
                    fallback_address = self._build_display_location(address, address, fallback_country)
                    return 39.9042, 116.4074, fallback_address, fallback_country
                time.sleep(self.backoff_factor ** attempt)

    def _calculate_optimal_angles(self, lat: float, install_type: str) -> tuple[float, float]:
        """Calculate optimal azimuth/tilt per design document"""
        abs_lat = abs(lat)
        azimuth = 180.0
        if install_type == "roof":
            tilt = max(10.0, abs_lat * 0.8)
        elif install_type == "ground":
            tilt = max(5.0, abs_lat)
        elif install_type == "hydro":
            tilt = max(5.0, abs_lat * 0.7)
        else:
            tilt = max(5.0, abs_lat)
        return round(azimuth, 1), round(tilt, 1)

    def run(self, validated_inputs: UserInputs) -> GeospatialData:
        """Run full geospatial processing pipeline"""
        self.log("Starting geospatial processing")

        lat, lon, formatted_address, country_name = self._address_to_coordinates(validated_inputs.project_address)
        azimuth, tilt = self._calculate_optimal_angles(lat, validated_inputs.install_type)

        geospatial_data = self.validate_schema({
            "latitude": lat,
            "longitude": lon,
            "formatted_address": formatted_address,
            "country_name": country_name,
            "optimal_azimuth": azimuth,
            "optimal_tilt": tilt
        }, GeospatialData)

        self.log(
            f"Location: {formatted_address} | Coordinates: {lat}, {lon} | "
            f"Azimuth: {azimuth}° | Tilt: {tilt}°"
        )
        return geospatial_data
