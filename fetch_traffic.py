import os
import requests
from django.core.management.base import BaseCommand
from authentication.models import CityMetric


BANGLADESH_CITY_POINTS = {
    "Dhaka": [
        (23.8103, 90.4125),
        (23.7806, 90.2794),
        (23.7465, 90.3760),
    ],
    "Chattogram": [
        (22.3569, 91.7832),
        (22.3350, 91.8325),
        (22.3667, 91.8000),
    ],
    "Rajshahi": [
        (24.3745, 88.6042),
        (24.3636, 88.6241),
        (24.3950, 88.6140),
    ],
    "Khulna": [
        (22.8456, 89.5403),
        (22.8200, 89.5500),
        (22.8700, 89.5250),
    ],
    "Sylhet": [
        (24.8949, 91.8687),
        (24.8990, 91.8710),
        (24.8800, 91.8600),
    ],
    "Barishal": [
        (22.7010, 90.3535),
        (22.6900, 90.3650),
        (22.7150, 90.3400),
    ],
}


class Command(BaseCommand):
    help = "Fetch real-time traffic data for Bangladesh cities using TomTom Traffic API"

    def handle(self, *args, **kwargs):
        api_key = os.getenv("TOMTOM_API_KEY")

        if not api_key:
            self.stdout.write(self.style.ERROR("TOMTOM_API_KEY is missing."))
            self.stdout.write("Set it first, then run this command again.")
            return

        for city_name, points in BANGLADESH_CITY_POINTS.items():
            travel_times = []
            current_speeds = []
            free_flow_speeds = []

            for lat, lon in points:
                url = (
                    "https://api.tomtom.com/traffic/services/4/"
                    f"flowSegmentData/absolute/10/json"
                    f"?point={lat},{lon}&unit=KMPH&key={api_key}"
                )

                try:
                    response = requests.get(url, timeout=15)
                    data = response.json()

                    flow = data.get("flowSegmentData", {})

                    current_speed = flow.get("currentSpeed")
                    free_flow_speed = flow.get("freeFlowSpeed")
                    current_travel_time = flow.get("currentTravelTime")

                    if current_travel_time is not None:
                        travel_times.append(float(current_travel_time) / 60)

                    if current_speed is not None:
                        current_speeds.append(float(current_speed))

                    if free_flow_speed is not None:
                        free_flow_speeds.append(float(free_flow_speed))

                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"{city_name}: traffic fetch failed for {lat},{lon}: {e}")
                    )

            if travel_times:
                avg_traffic_minutes = round(sum(travel_times) / len(travel_times), 1)
            elif current_speeds and free_flow_speeds:
                avg_current_speed = sum(current_speeds) / len(current_speeds)
                avg_free_flow_speed = sum(free_flow_speeds) / len(free_flow_speeds)

                congestion_ratio = avg_free_flow_speed / avg_current_speed if avg_current_speed > 0 else 1
                avg_traffic_minutes = round(20 * congestion_ratio, 1)
            else:
                avg_traffic_minutes = None

            metric, created = CityMetric.objects.get_or_create(city_name=city_name)

            if avg_traffic_minutes is not None:
                metric.traffic_minutes_latest = avg_traffic_minutes
                metric.traffic_source = "TomTom Traffic Flow API"
                metric.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{city_name}: traffic updated = {avg_traffic_minutes} min"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"{city_name}: no traffic value returned")
                )