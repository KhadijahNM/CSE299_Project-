import requests
from django.core.management.base import BaseCommand
from ...models import AirQualityReading, CityMetric, City, PollutionData

CITY_GEO = {
    "Dhaka": (23.8103, 90.4125),
    "Chattogram": (22.3569, 91.7832),
    "Sylhet": (24.8949, 91.8687),
    "Khulna": (22.8456, 89.5403),
    "Rajshahi": (24.3636, 88.6241),
}

OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def get_air_quality_level(pm25):
    if pm25 is None:
        return "Unknown"
    if pm25 <= 12:
        return "Good"
    elif pm25 <= 35.4:
        return "Moderate"
    elif pm25 <= 55.4:
        return "Unhealthy for Sensitive Groups"
    elif pm25 <= 150.4:
        return "Unhealthy"
    elif pm25 <= 250.4:
        return "Very Unhealthy"
    else:
        return "Hazardous"


class Command(BaseCommand):
    help = "Fetch PM2.5 from Open-Meteo Air Quality API and store in DB"

    def handle(self, *args, **options):
        for city_name, (lat, lon) in CITY_GEO.items():
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "pm2_5",
                "hourly": "pm2_5",
                "timezone": "Asia/Dhaka",
            }

            try:
                r = requests.get(OPEN_METEO_AQ_URL, params=params, timeout=20)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                self.stderr.write(f"[{city_name}] request failed: {e}")
                continue

            pm25 = None

            # 1) Try current PM2.5 first
            try:
                pm25 = data.get("current", {}).get("pm2_5")
            except Exception:
                pm25 = None

            # 2) Fallback: take the first non-None hourly value
            if pm25 is None:
                try:
                    pm25_list = data.get("hourly", {}).get("pm2_5", [])
                    for value in pm25_list:
                        if value is not None:
                            pm25 = value
                            break
                except Exception:
                    pm25 = None

            air_quality_level = get_air_quality_level(pm25)

            # Ensure City exists
            city_obj, _ = City.objects.get_or_create(city_name=city_name)

            # 1. Save raw reading history
            AirQualityReading.objects.create(
                city_name=city_name,
                pm25=pm25,
                aqi=None,
                source="Open-Meteo Air Quality API",
                raw_json=data,
            )

            # 2. Update latest snapshot table
            CityMetric.objects.update_or_create(
                city_name=city_name,
                defaults={
                    "pm25_latest": pm25,
                    "aqi_latest": None,
                    "aqi_source": "Open-Meteo Air Quality API",
                }
            )

            # 3. Update PollutionData table
            PollutionData.objects.update_or_create(
                city=city_obj,
                defaults={
                    "pm25": pm25,
                    "air_quality_level": air_quality_level,
                    "estimated_vehicle_emission": None,
                    "source": "Open-Meteo Air Quality API",
                    "raw_json": data,
                }
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{city_name}] PM2.5={pm25} | Level={air_quality_level}"
                )
            )

        self.stdout.write(self.style.SUCCESS("✅ Open-Meteo PM2.5 fetch complete."))