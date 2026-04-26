from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta

from .forms import SignUpForm, SignInForm
from .models import (
    Profile,
    CitizenData,
    PolicymakerData,
    CorporateData,
    City,
    QoLIndex,
    CityMetric,
    HistoricalAQI,
    TrafficData,
    ExternalCitizenSurvey,
)


def home(request):
    return render(request, "authentication/index.html")


def signup(request):
    form = SignUpForm()

    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            confirm_password = form.cleaned_data["confirm_password"]
            role = form.cleaned_data["role"]

            if password != confirm_password:
                return render(request, "authentication/signup.html", {
                    "form": form,
                    "error": "Passwords do not match."
                })

            if User.objects.filter(username=username).exists():
                return render(request, "authentication/signup.html", {
                    "form": form,
                    "error": "Username already exists."
                })

            if User.objects.filter(email=email).exists():
                return render(request, "authentication/signup.html", {
                    "form": form,
                    "error": "Email already exists."
                })

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            Profile.objects.create(user=user, role=role)
            return redirect("signin")

    return render(request, "authentication/signup.html", {"form": form})


def signin(request):
    form = SignInForm()

    if request.method == "POST":
        form = SignInForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect_by_role(user)

            return render(request, "authentication/signin.html", {
                "form": form,
                "error": "Invalid username or password."
            })

    return render(request, "authentication/signin.html", {"form": form})


def signout(request):
    logout(request)
    return redirect("home")


def redirect_by_role(user):
    try:
        profile = Profile.objects.get(user=user)

        if profile.role == "citizen":
            return redirect("citizen_dashboard")
        if profile.role == "policymaker":
            return redirect("policymaker_dashboard")
        if profile.role == "corporate_leader":
            return redirect("corporate_dashboard")

    except Profile.DoesNotExist:
        pass

    return redirect("home")


def admin_signin(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            return redirect("admin_overview")

        error = "Only admin can log in here."

    return render(request, "authentication/admin_signin.html", {"error": error})


# =========================================================
# Policy recommendation helper functions
# =========================================================

DEMO_CITIES = ["Dhaka", "Chattogram", "Sylhet", "Khulna", "Rajshahi", "Barishal"]


def safe_float(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def pm25_to_aqi(pm25):
    if pm25 is None:
        return None

    pm25 = float(pm25)

    if pm25 <= 12:
        return round((50 / 12) * pm25, 1)
    if pm25 <= 35.4:
        return round(51 + ((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1), 1)
    if pm25 <= 55.4:
        return round(101 + ((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5), 1)
    if pm25 <= 150.4:
        return round(151 + ((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5), 1)
    if pm25 <= 250.4:
        return round(201 + ((300 - 201) / (250.4 - 150.5)) * (pm25 - 150.5), 1)

    return 301


def risk_label(pm25):
    if pm25 is None:
        return ("Unknown", "No real-time value yet", "#6b7280")

    if pm25 <= 12:
        return ("Good", "Air quality is good", "#16a34a")
    if pm25 <= 35.4:
        return ("Moderate", "Air is acceptable", "#eab308")
    if pm25 <= 55.4:
        return ("Unhealthy for Sensitive Groups", "Sensitive people should limit outdoor exposure", "#f97316")
    if pm25 <= 150.4:
        return ("Unhealthy", "Reduce prolonged outdoor exposure", "#ef4444")
    if pm25 <= 250.4:
        return ("Very Unhealthy", "Health warning for everyone", "#7c3aed")

    return ("Hazardous", "Serious health risk", "#7f1d1d")


def normalize_low_is_good(value, max_value):
    value = safe_float(value, 0)

    if value <= 0:
        return 55

    score = 100 - ((value / max_value) * 100)
    return max(0, min(100, score))


def normalize_high_is_good(value):
    value = safe_float(value, 55)
    return max(0, min(100, value))


def get_city_names():
    city_names = list(City.objects.values_list("city_name", flat=True))

    if not city_names:
        return DEMO_CITIES

    return city_names


def get_city_pm25(city_name):
    metric = CityMetric.objects.filter(city_name__iexact=city_name).first()

    if metric and metric.pm25_latest is not None:
        return metric.pm25_latest, metric.aqi_source, metric.last_updated

    historical_pm25 = HistoricalAQI.objects.filter(
        city_name__iexact=city_name
    ).aggregate(avg=Avg("pm25"))["avg"]

    if historical_pm25 is not None:
        return historical_pm25, "Historical AQI Dataset", None

    return None, "No AQI source available", None


def get_city_aqi(city_name, pm25):
    metric = CityMetric.objects.filter(city_name__iexact=city_name).first()

    if metric and metric.aqi_latest is not None:
        return metric.aqi_latest

    return pm25_to_aqi(pm25)


def get_city_traffic(city_name):
    import random

    metric = CityMetric.objects.filter(city_name__iexact=city_name).first()

    if metric and metric.traffic_minutes_latest is not None:
        return metric.traffic_minutes_latest, "Stored latest traffic metric"

    traffic_avg = TrafficData.objects.filter(
        city__city_name__iexact=city_name
    ).aggregate(avg=Avg("avg_commute_time_minutes"))["avg"]

    if traffic_avg is not None:
        simulated = round(float(traffic_avg) + random.uniform(-5, 10), 1)
        simulated = max(5, simulated)
        return simulated, "Simulated real-time traffic based on stored dataset"

    citizen_avg = CitizenData.objects.filter(
        current_city__iexact=city_name
    ).aggregate(avg=Avg("commute_time"))["avg"]

    if citizen_avg is not None:
        simulated = round(float(citizen_avg) + random.uniform(-5, 10), 1)
        simulated = max(5, simulated)
        return simulated, "Simulated real-time traffic based on citizen commute data"

    fallback_traffic = {
        "Dhaka": 65,
        "Chattogram": 45,
        "Rajshahi": 28,
        "Khulna": 32,
        "Sylhet": 30,
        "Barishal": 25,
    }

    if city_name in fallback_traffic:
        simulated = round(fallback_traffic[city_name] + random.uniform(-4, 8), 1)
        return simulated, "Simulated real-time traffic baseline"

    return None, "No traffic source available"


def build_air_cards(cities=DEMO_CITIES, baseline_limit=1000):
    cards = []

    for city in cities:
        now_pm25, source, updated_at = get_city_pm25(city)

        baseline_qs = HistoricalAQI.objects.filter(
            city_name__iexact=city
        ).order_by("-recorded_at")[:baseline_limit]

        baseline_pm25 = baseline_qs.aggregate(avg=Avg("pm25"))["avg"]

        now_pm25 = round(now_pm25, 1) if now_pm25 is not None else None
        baseline_pm25 = round(float(baseline_pm25), 1) if baseline_pm25 is not None else None

        delta = None
        if now_pm25 is not None and baseline_pm25 is not None:
            delta = round(now_pm25 - baseline_pm25, 1)

        label, note, color = risk_label(now_pm25)

        cards.append({
            "city": city,
            "now_pm25": now_pm25,
            "baseline_pm25": baseline_pm25,
            "delta_pm25": delta,
            "risk_label": label,
            "risk_note": note,
            "risk_color": color,
            "source": source,
            "updated_at": updated_at,
        })

    return cards


def policy_input_boost(policymaker_data):
    boost = 0

    if policymaker_data.infrastructure_pressure == "high":
        boost += 8
    elif policymaker_data.infrastructure_pressure == "medium":
        boost += 5

    if policymaker_data.migration_trend == "increasing":
        boost += 6
    elif policymaker_data.migration_trend == "stable":
        boost += 3

    if policymaker_data.budget_level == "high":
        boost += 5
    elif policymaker_data.budget_level == "medium":
        boost += 3

    statuses = [
        policymaker_data.housing_status,
        policymaker_data.transport_status,
        policymaker_data.employment_status,
        policymaker_data.environmental_status,
    ]

    for status in statuses:
        if status == "poor":
            boost += 4
        elif status == "average":
            boost += 2

    return boost


def citizen_need_score_for_city(city_name):
    saved_preferred = CitizenData.objects.filter(preferred_city__iexact=city_name).count()
    saved_current = CitizenData.objects.filter(current_city__iexact=city_name).count()

    external_preferred = ExternalCitizenSurvey.objects.filter(preferred_city__iexact=city_name).count()
    external_current = ExternalCitizenSurvey.objects.filter(current_city__iexact=city_name).count()

    total = CitizenData.objects.count() + ExternalCitizenSurvey.objects.count()

    if total == 0:
        return 50

    score = (
        saved_preferred * 1.5 +
        external_preferred * 1.5 +
        saved_current * 0.8 +
        external_current * 0.8
    ) / total * 100

    return max(30, min(100, score))


def generate_policy_recommendations(policymaker_data):
    city_names = get_city_names()

    recommendations = []
    input_boost = policy_input_boost(policymaker_data)

    for city_name in city_names:
        city = City.objects.filter(city_name__iexact=city_name).first()
        qol = QoLIndex.objects.filter(city__city_name__iexact=city_name).order_by("-id").first()

        pm25, aqi_source, updated_at = get_city_pm25(city_name)
        aqi = get_city_aqi(city_name, pm25)
        traffic, traffic_source = get_city_traffic(city_name)

        air_score = normalize_low_is_good(pm25, 160)
        traffic_score = normalize_low_is_good(traffic, 120)
        infrastructure_score = normalize_high_is_good(city.infrastructure_score if city else 55)
        healthcare_score = normalize_high_is_good(qol.healthcare_score if qol else 55)
        education_score = normalize_high_is_good(qol.education_score if qol else 55)
        housing_score = normalize_high_is_good(qol.housing_score if qol else 55)
        citizen_score = citizen_need_score_for_city(city_name)

        final_score = (
            air_score * 0.22 +
            traffic_score * 0.16 +
            infrastructure_score * 0.18 +
            healthcare_score * 0.10 +
            education_score * 0.10 +
            housing_score * 0.10 +
            citizen_score * 0.14 +
            input_boost
        )

        final_score = round(min(100, final_score), 2)

        problems = []

        if pm25 and pm25 > 35.4:
            problems.append("Air pollution concern")
        if traffic and traffic > 40:
            problems.append("Traffic congestion")
        if infrastructure_score < 60:
            problems.append("Infrastructure gap")
        if housing_score < 60:
            problems.append("Housing pressure")
        if citizen_score > 60:
            problems.append("High citizen relocation demand")

        if not problems:
            problems.append("Balanced city profile with moderate planning need")

        recommendations.append({
            "city": city_name,
            "score": final_score,
            "pm25": round(safe_float(pm25), 1) if pm25 is not None else None,
            "aqi": round(safe_float(aqi), 1) if aqi is not None else None,
            "traffic": round(safe_float(traffic), 1) if traffic is not None else None,
            "citizen_score": round(citizen_score, 1),
            "infrastructure_score": round(infrastructure_score, 1),
            "healthcare_score": round(healthcare_score, 1),
            "education_score": round(education_score, 1),
            "housing_score": round(housing_score, 1),
            "main_problems": problems,
            "aqi_source": aqi_source,
            "traffic_source": traffic_source,
            "updated_at": updated_at,
        })

    recommendations = sorted(
        recommendations,
        key=lambda x: x["score"],
        reverse=True
    )[:3]

    fixed_ranks = [
        ("Best", "best", "Highest priority city for policy action and infrastructure planning."),
        ("Good", "good", "Strong candidate for phased public service and infrastructure expansion."),
        ("Moderate", "moderate", "Needs monitoring before large-scale intervention."),
    ]

    for index, rec in enumerate(recommendations):
        rec["rank"] = fixed_ranks[index][0]
        rec["rank_class"] = fixed_ranks[index][1]
        rec["suggested_action"] = fixed_ranks[index][2]

    return recommendations


# =========================================================
# New policy intelligence features
# =========================================================

def change_direction_for_low_is_good(change_value):
    if change_value is None:
        return "neutral"
    if change_value < 0:
        return "good"
    if change_value > 0:
        return "bad"
    return "neutral"


def change_direction_for_high_is_good(change_value):
    if change_value is None:
        return "neutral"
    if change_value > 0:
        return "good"
    if change_value < 0:
        return "bad"
    return "neutral"


def format_change(value, suffix="%"):
    if value is None:
        return "N/A"

    if value > 0:
        return f"+{value}{suffix}"
    if value < 0:
        return f"{value}{suffix}"

    return f"0{suffix}"


def get_avg_historical_value(city_name, field_name, start_date, end_date):
    filter_kwargs = {
        "city_name__iexact": city_name,
        "recorded_at__gte": start_date,
        "recorded_at__lt": end_date,
    }

    return HistoricalAQI.objects.filter(**filter_kwargs).aggregate(
        avg=Avg(field_name)
    )["avg"]


def calculate_percentage_change(old_value, new_value):
    old_value = safe_float(old_value, None)
    new_value = safe_float(new_value, None)

    if old_value in [None, 0] or new_value is None:
        return None

    return round(((new_value - old_value) / old_value) * 100, 1)


def build_time_based_trend_analysis(cities=None):
    if cities is None:
        cities = get_city_names()

    now = timezone.now()
    six_months_ago = now - timedelta(days=180)
    three_months_ago = now - timedelta(days=90)

    trend_cards = []

    for city_name in cities:
        old_aqi = get_avg_historical_value(city_name, "aqi", six_months_ago, three_months_ago)
        recent_aqi = get_avg_historical_value(city_name, "aqi", three_months_ago, now)

        old_pm25 = get_avg_historical_value(city_name, "pm25", six_months_ago, three_months_ago)
        recent_pm25 = get_avg_historical_value(city_name, "pm25", three_months_ago, now)

        aqi_change = calculate_percentage_change(old_aqi, recent_aqi)
        pm25_change = calculate_percentage_change(old_pm25, recent_pm25)

        current_traffic, traffic_source = get_city_traffic(city_name)

        fallback_traffic_baseline = {
            "Dhaka": 60,
            "Chattogram": 42,
            "Rajshahi": 30,
            "Khulna": 34,
            "Sylhet": 32,
            "Barishal": 28,
        }

        baseline_traffic = fallback_traffic_baseline.get(city_name, 35)
        traffic_change = calculate_percentage_change(baseline_traffic, current_traffic)

        current_mentions = (
            CitizenData.objects.filter(current_city__iexact=city_name).count() +
            ExternalCitizenSurvey.objects.filter(current_city__iexact=city_name).count()
        )

        preferred_mentions = (
            CitizenData.objects.filter(preferred_city__iexact=city_name).count() +
            ExternalCitizenSurvey.objects.filter(preferred_city__iexact=city_name).count()
        )

        if current_mentions == 0:
            relocation_change = None
        else:
            relocation_change = round(((preferred_mentions - current_mentions) / current_mentions) * 100, 1)

        trend_cards.append({
            "city": city_name,
            "aqi_change": {
                "value": format_change(aqi_change),
                "direction": change_direction_for_low_is_good(aqi_change),
            },
            "pm25_change": {
                "value": format_change(pm25_change),
                "direction": change_direction_for_low_is_good(pm25_change),
            },
            "traffic_change": {
                "value": format_change(traffic_change),
                "direction": change_direction_for_low_is_good(traffic_change),
            },
            "relocation_demand_change": {
                "value": format_change(relocation_change),
                "direction": change_direction_for_high_is_good(relocation_change),
            },
            "traffic_source": traffic_source,
        })

    return trend_cards


def build_profitability_estimates(recommendations):
    estimates = []

    for rec in recommendations:
        city_name = rec["city"]

        infrastructure_score = safe_float(rec.get("infrastructure_score"), 55)
        citizen_score = safe_float(rec.get("citizen_score"), 50)
        traffic = safe_float(rec.get("traffic"), 35)
        pm25 = safe_float(rec.get("pm25"), 35)

        revenue_growth = round(
            5 +
            (citizen_score * 0.08) +
            (infrastructure_score * 0.04),
            1
        )

        service_saving = round(
            3 +
            normalize_low_is_good(traffic, 120) * 0.06 +
            normalize_low_is_good(pm25, 160) * 0.04,
            1
        )

        setup_cost_pressure = round(
            max(5, 28 - (infrastructure_score * 0.18)),
            1
        )

        net_gain = round(revenue_growth + service_saving - setup_cost_pressure, 1)

        if net_gain >= 12:
            roi_label = "High public return potential"
        elif net_gain >= 6:
            roi_label = "Moderate public return potential"
        elif net_gain >= 0:
            roi_label = "Limited but positive return"
        else:
            roi_label = "High cost-risk before expansion"

        estimates.append({
            "city": city_name,
            "revenue_growth": revenue_growth,
            "service_saving": service_saving,
            "setup_cost_pressure": setup_cost_pressure,
            "net_gain": net_gain,
            "roi_label": roi_label,
        })

    return estimates


def count_problem_mentions(city_name):
    problem_keywords = [
        "traffic",
        "pollution",
        "cost",
        "housing",
        "job",
        "health",
        "education",
        "transport",
        "congestion",
        "expensive",
        "unsafe",
        "problem",
    ]

    count = 0

    citizen_notes = CitizenData.objects.filter(
        current_city__iexact=city_name
    ).exclude(additional_notes__isnull=True).exclude(additional_notes="")

    for item in citizen_notes:
        note = item.additional_notes.lower()
        if any(keyword in note for keyword in problem_keywords):
            count += 1

    external_notes = ExternalCitizenSurvey.objects.filter(
        current_city__iexact=city_name
    )

    for item in external_notes:
        text = f"{item.main_problem or ''} {item.relocation_reason or ''}".lower()
        if any(keyword in text for keyword in problem_keywords):
            count += 1

    return count


def build_citizen_satisfaction_feedback(cities=None):
    if cities is None:
        cities = get_city_names()

    feedback = []

    for city_name in cities:
        current_mentions = (
            CitizenData.objects.filter(current_city__iexact=city_name).count() +
            ExternalCitizenSurvey.objects.filter(current_city__iexact=city_name).count()
        )

        preferred_mentions = (
            CitizenData.objects.filter(preferred_city__iexact=city_name).count() +
            ExternalCitizenSurvey.objects.filter(preferred_city__iexact=city_name).count()
        )

        complaint_mentions = count_problem_mentions(city_name)

        if current_mentions == 0 and preferred_mentions == 0:
            satisfaction_score = 50
        else:
            satisfaction_score = 50
            satisfaction_score += preferred_mentions * 12
            satisfaction_score -= complaint_mentions * 10
            satisfaction_score -= current_mentions * 2
            satisfaction_score = max(0, min(100, satisfaction_score))

        if satisfaction_score >= 75:
            label = "Strong citizen acceptance"
        elif satisfaction_score >= 55:
            label = "Moderate citizen acceptance"
        elif satisfaction_score >= 35:
            label = "Needs policy attention"
        else:
            label = "Low satisfaction signal"

        feedback.append({
            "city": city_name,
            "satisfaction_score": round(satisfaction_score, 1),
            "current_mentions": current_mentions,
            "preferred_mentions": preferred_mentions,
            "complaint_mentions": complaint_mentions,
            "label": label,
        })

    feedback = sorted(
        feedback,
        key=lambda x: x["satisfaction_score"],
        reverse=True
    )

    return feedback


# =========================================================
# Dashboards
# =========================================================

@login_required(login_url="signin")
def citizen_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != "citizen":
            return redirect_by_role(request.user)
    except Profile.DoesNotExist:
        return redirect("home")

    success = False
    citizen_data, created = CitizenData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        citizen_data.current_city = request.POST.get("current_city")
        citizen_data.preferred_city = request.POST.get("preferred_city")
        citizen_data.job_sector = request.POST.get("job_sector")
        citizen_data.salary_range = request.POST.get("salary_range")

        commute_time = request.POST.get("commute_time")
        citizen_data.commute_time = int(commute_time) if commute_time else None

        citizen_data.transport_mode = request.POST.get("transport_mode")
        citizen_data.housing_priority = request.POST.get("housing_priority")
        citizen_data.health_priority = request.POST.get("health_priority")
        citizen_data.education_priority = request.POST.get("education_priority")
        citizen_data.cost_priority = request.POST.get("cost_priority")
        citizen_data.additional_notes = request.POST.get("additional_notes")

        citizen_data.save()
        success = True

    return render(request, "authentication/citizen_dashboard.html", {
        "citizen_data": citizen_data,
        "success": success,
        "air_cards": build_air_cards(),
    })


@login_required(login_url="signin")
def policymaker_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != "policymaker":
            return redirect_by_role(request.user)
    except Profile.DoesNotExist:
        return redirect("home")

    success = False
    policymaker_data, created = PolicymakerData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        policymaker_data.target_city = request.POST.get("target_city", "")
        policymaker_data.policy_focus = request.POST.get("policy_focus", "")
        policymaker_data.migration_trend = request.POST.get("migration_trend", "")
        policymaker_data.infrastructure_pressure = request.POST.get("infrastructure_pressure", "")
        policymaker_data.housing_status = request.POST.get("housing_status", "")
        policymaker_data.transport_status = request.POST.get("transport_status", "")
        policymaker_data.employment_status = request.POST.get("employment_status", "")
        policymaker_data.environmental_status = request.POST.get("environmental_status", "")
        policymaker_data.budget_level = request.POST.get("budget_level", "")
        policymaker_data.policy_notes = request.POST.get("policy_notes", "")

        policymaker_data.save()
        success = True

    recommendations = generate_policy_recommendations(policymaker_data)
    city_names = get_city_names()

    context = {
        "policymaker_data": policymaker_data,
        "success": success,
        "recommendations": recommendations,
        "total_citizen_inputs": CitizenData.objects.count() + ExternalCitizenSurvey.objects.count(),
        "total_monitored_cities": len(city_names),

        "trend_analysis": build_time_based_trend_analysis(city_names),
        "profitability_estimates": build_profitability_estimates(recommendations),
        "citizen_satisfaction_feedback": build_citizen_satisfaction_feedback(city_names),
    }

    return render(request, "authentication/policymaker_dashboard.html", context)


@login_required(login_url="signin")
def corporate_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != "corporate_leader":
            return redirect_by_role(request.user)
    except Profile.DoesNotExist:
        return redirect("home")

    success = False
    corporate_data, created = CorporateData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        corporate_data.company_name = request.POST.get("company_name")
        corporate_data.business_sector = request.POST.get("business_sector")
        corporate_data.current_city = request.POST.get("current_city")
        corporate_data.target_city = request.POST.get("target_city")

        employee_count = request.POST.get("employee_count")
        corporate_data.employee_count = int(employee_count) if employee_count else None

        corporate_data.office_cost_level = request.POST.get("office_cost_level")
        corporate_data.talent_availability = request.POST.get("talent_availability")
        corporate_data.infrastructure_quality = request.POST.get("infrastructure_quality")
        corporate_data.business_growth_status = request.POST.get("business_growth_status")
        corporate_data.relocation_interest = request.POST.get("relocation_interest")
        corporate_data.corporate_notes = request.POST.get("corporate_notes")

        corporate_data.save()
        success = True

    return render(request, "authentication/corporate_dashboard.html", {
        "corporate_data": corporate_data,
        "success": success,
        "air_cards": build_air_cards(),
    })


@login_required(login_url="signin")
def admin_overview(request):
    if not request.user.is_superuser:
        return HttpResponse("You are not allowed to access this page.")

    context = {
        "total_users": User.objects.count(),
        "total_citizens": Profile.objects.filter(role="citizen").count(),
        "total_policymakers": Profile.objects.filter(role="policymaker").count(),
        "total_corporates": Profile.objects.filter(role="corporate_leader").count(),
        "citizen_forms": CitizenData.objects.count(),
        "policymaker_forms": PolicymakerData.objects.count(),
        "corporate_forms": CorporateData.objects.count(),
        "recent_users": User.objects.order_by("-date_joined")[:5],
    }

    return render(request, "authentication/admin_overview.html", context)