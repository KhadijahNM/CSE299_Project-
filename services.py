import os
import requests
from .models import CityData


DIVISIONAL_CITIES = [
    "Dhaka",
    "Chattogram",
    "Rajshahi",
    "Khulna",
    "Sylhet",
    "Barishal",
]


def convert_priority(value):
    if value is None or value == "":
        return 5

    if isinstance(value, int):
        return value

    value = str(value).strip().lower()

    if value == "low":
        return 3
    elif value == "medium":
        return 5
    elif value == "high":
        return 8

    try:
        return int(value)
    except ValueError:
        return 5


def get_city_recommendations(citizen):
    cities = CityData.objects.exclude(city_name__iexact=citizen.current_city)

    cost_weight = convert_priority(citizen.cost_priority)
    health_weight = convert_priority(citizen.health_priority)
    education_weight = convert_priority(citizen.education_priority)
    housing_weight = convert_priority(citizen.housing_priority)

    time_weight = 5
    if citizen.commute_time:
        if citizen.commute_time >= 180:
            time_weight = 12
        elif citizen.commute_time >= 90:
            time_weight = 10
        elif citizen.commute_time >= 60:
            time_weight = 8
        elif citizen.commute_time >= 30:
            time_weight = 6

    recommendations = []

    for city in cities:
        score = 0

        score += cost_weight * city.living_cost_score
        score += health_weight * city.air_quality_score
        score += education_weight * city.education_score
        score += housing_weight * city.healthcare_score
        score += time_weight * city.traffic_score

        if citizen.preferred_city and city.city_name.lower() == citizen.preferred_city.lower():
            score += 8

        if citizen.salary_range == "low":
            score += city.living_cost_score * 2
        elif citizen.salary_range == "high":
            score += city.job_opportunity_score * 2

        if citizen.job_sector == "it":
            score += city.remote_work_score * 2
        elif citizen.job_sector == "business":
            score += city.job_opportunity_score * 2
        elif citizen.job_sector == "education":
            score += city.education_score * 2
        elif citizen.job_sector == "health":
            score += city.healthcare_score * 2
        elif citizen.job_sector == "government":
            score += city.traffic_score

        if citizen.transport_mode in ["bus", "train"]:
            score += city.traffic_score * 1.5
        elif citizen.transport_mode in ["walk", "bike"]:
            score += city.air_quality_score

        reasons = []

        if city.living_cost_score >= 7:
            reasons.append("lower living cost")
        if city.air_quality_score >= 7:
            reasons.append("cleaner air")
        if city.education_score >= 7:
            reasons.append("better education access")
        if city.healthcare_score >= 7:
            reasons.append("strong healthcare access")
        if city.traffic_score >= 7:
            reasons.append("shorter commute")
        if citizen.preferred_city and city.city_name.lower() == citizen.preferred_city.lower():
            reasons.append("matches your preferred city")

        recommendations.append({
            "city": city,
            "score": round(score, 2),
            "reasons": reasons[:4],
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:3]


def get_best_city_comparison(citizen):
    recommendations = get_city_recommendations(citizen)

    if not recommendations:
        return None

    best_match = recommendations[0]
    best_city = best_match["city"]

    current_commute = citizen.commute_time if citizen.commute_time else 0
    new_commute = best_city.avg_commute_minutes
    time_saved = max(current_commute - new_commute, 0)

    return {
        "current_city": citizen.current_city,
        "recommended_city": best_city.city_name,
        "current_commute": current_commute,
        "recommended_commute": new_commute,
        "time_saved": time_saved,
        "recommended_rent": best_city.avg_monthly_rent,
        "recommendation_score": best_match["score"],
        "reasons": best_match["reasons"],
    }


def get_city_coordinates(city_name):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    results = data.get("results")
    if not results:
        return None

    first = results[0]

    return {
        "lat": first["latitude"],
        "lon": first["longitude"],
        "name": first["name"],
    }


def get_live_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    current = data.get("current")
    if not current:
        return None

    weather_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
    }

    code = current.get("weather_code")

    return {
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "weather": weather_map.get(code, f"Weather code {code}"),
        "wind_speed": current.get("wind_speed_10m"),
    }


def get_live_traffic(lat, lon):
    api_key = os.getenv("TOMTOM_API_KEY")

    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {
        "point": f"{lat},{lon}",
        "key": api_key,
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json().get("flowSegmentData", {})

    return {
        "current_speed": data.get("currentSpeed"),
        "free_flow_speed": data.get("freeFlowSpeed"),
        "current_travel_time": data.get("currentTravelTime"),
        "free_flow_travel_time": data.get("freeFlowTravelTime"),
        "road_closure": data.get("roadClosure"),
    }


def get_live_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm10,pm2_5",
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    current = data.get("current")
    if not current:
        return None

    pm25 = current.get("pm2_5")
    pm10 = current.get("pm10")

    if pm25 is None:
        pollution_label = "Unknown"
    elif pm25 <= 15:
        pollution_label = "Good"
    elif pm25 <= 35:
        pollution_label = "Moderate"
    elif pm25 <= 55:
        pollution_label = "Unhealthy for Sensitive Groups"
    elif pm25 <= 150:
        pollution_label = "Unhealthy"
    elif pm25 <= 250:
        pollution_label = "Very Unhealthy"
    else:
        pollution_label = "Hazardous"

    return {
        "pm2_5": pm25,
        "pm10": pm10,
        "pollution_label": pollution_label,
    }


def build_observed_issue_and_policy(city, affordability, environment, healthcare, traffic, air):
    issues = []
    actions = []

    pm25 = air.get("pm2_5") if air else None

    if pm25 is not None and pm25 > 35:
        issues.append("Air pollution needs attention")
        actions.append("Increase green zones and strengthen pollution control")

    if traffic < 7:
        issues.append("Traffic and commute pressure may affect operations")
        actions.append("Improve public transport and business-area road connectivity")

    if affordability < 7:
        issues.append("Office and living cost may be comparatively high")
        actions.append("Develop affordable commercial zones and support lower-cost office spaces")

    if healthcare < 7:
        issues.append("Healthcare access can be improved")
        actions.append("Expand healthcare facilities near business and residential areas")

    if environment < 7:
        issues.append("Environmental quality needs improvement")
        actions.append("Promote cleaner energy, waste control, and urban greenery")

    if not issues:
        issues.append("City conditions are balanced for business relocation")
        actions.append("Maintain current infrastructure quality and business-friendly policies")

    return issues[0], actions[0]


def get_top_divisional_city_recommendations(corporate_data):
    recommendations = []

    for city_name in DIVISIONAL_CITIES:
        try:
            city = CityData.objects.get(city_name__iexact=city_name)
        except CityData.DoesNotExist:
            continue

        coords = get_city_coordinates(city.city_name)

        if coords:
            air = get_live_air_quality(coords["lat"], coords["lon"])
        else:
            air = None

        avg_rent = city.avg_monthly_rent
        avg_utility = getattr(city, "avg_monthly_utility", 2200)
        avg_commute = city.avg_commute_minutes

        healthcare = city.healthcare_score
        traffic = city.traffic_score
        affordability = city.living_cost_score
        environment = city.air_quality_score

        estimated_monthly_cost = avg_rent + avg_utility
        estimated_monthly_saving = None
        air_quality_comparison = None

        if corporate_data.current_city:
            try:
                current_city = CityData.objects.get(city_name__iexact=corporate_data.current_city)
                current_city_cost = current_city.avg_monthly_rent + getattr(current_city, "avg_monthly_utility", 2200)
                estimated_monthly_saving = current_city_cost - estimated_monthly_cost

                if current_city.air_quality_score:
                    diff = ((environment - current_city.air_quality_score) / current_city.air_quality_score) * 100
                    air_quality_comparison = round(max(min(diff, 100), -100), 1)

            except CityData.DoesNotExist:
                pass

        score = 0
        score += affordability * 3
        score += healthcare * 2
        score += environment * 2
        score += traffic * 2

        if corporate_data.office_cost_level == "low":
            score += affordability * 2
        elif corporate_data.office_cost_level == "high":
            score += city.job_opportunity_score

        if corporate_data.talent_availability == "high":
            score += city.job_opportunity_score * 2

        if corporate_data.infrastructure_quality == "good":
            score += city.remote_work_score + city.traffic_score

        if air and air.get("pm2_5") is not None:
            score += max(0, 120 - air["pm2_5"]) / 10

        observed_issues, suggested_policy_action = build_observed_issue_and_policy(
            city=city,
            affordability=affordability,
            environment=environment,
            healthcare=healthcare,
            traffic=traffic,
            air=air,
        )

        recommendations.append({
            "city": city.city_name,
            "match_score": round(score, 2),
            "avg_rent": avg_rent,
            "avg_utility": avg_utility,
            "avg_commute": avg_commute,
            "air_pollution": air["pm2_5"] if air else None,
            "air_pollution_label": air["pollution_label"] if air else "Unknown",
            "pm10": air["pm10"] if air else None,
            "pm2_5": air["pm2_5"] if air else None,
            "estimated_monthly_cost": estimated_monthly_cost,
            "estimated_monthly_saving": estimated_monthly_saving,
            "air_quality_comparison": air_quality_comparison,
            "affordability_score": round(affordability * 10, 1),
            "environment_score": round(environment * 10, 1),
            "healthcare_score": round(healthcare * 10, 1),
            "traffic_score": round(traffic * 10, 1),
            "observed_issues": observed_issues,
            "suggested_policy_action": suggested_policy_action,
        })

    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations[:3]