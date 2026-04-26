import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from google import genai
from .ml.predict import predict_city
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, SignInForm
from collections import Counter
from .models import Profile, CitizenData, PolicymakerData, CorporateData, CityData, SurveyResponse
from .services import (
    get_city_recommendations,
    get_best_city_comparison,
    get_city_coordinates,
    get_live_traffic,
    get_live_weather,
    get_top_divisional_city_recommendations,
)




def home(request):
    return render(request, "authentication/index.html")


def signup(request):
    form = SignUpForm()

    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data['confirm_password']
            role = form.cleaned_data['role']

            if password != confirm_password:
                return render(request, "authentication/signup.html", {
                    'form': form,
                    'error': "Passwords do not match."
                })

            if User.objects.filter(username=username).exists():
                return render(request, "authentication/signup.html", {
                    'form': form,
                    'error': "Username already exists. Please choose another one."
                })

            if User.objects.filter(email=email).exists():
                return render(request, "authentication/signup.html", {
                    'form': form,
                    'error': "Email already exists. Please use another email."
                })

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            Profile.objects.create(user=user, role=role)

            return redirect('signin')

    return render(request, "authentication/signup.html", {'form': form})


def signin(request):
    form = SignInForm()

    if request.method == "POST":
        form = SignInForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                try:
                    profile = Profile.objects.get(user=user)

                    if profile.role == 'citizen':
                        return redirect('citizen_dashboard')
                    elif profile.role == 'policymaker':
                        return redirect('policymaker_dashboard')
                    elif profile.role == 'corporate_leader':
                        return redirect('corporate_dashboard')
                    else:
                        return redirect('home')

                except Profile.DoesNotExist:
                    return render(request, "authentication/signin.html", {
                        'form': form,
                        'error': "No profile found for this user."
                    })

            else:
                return render(request, "authentication/signin.html", {
                    'form': form,
                    'error': "Invalid username or password."
                })

    return render(request, "authentication/signin.html", {'form': form})


def signout(request):
    logout(request)
    return redirect('home')


def redirect_by_role(user):
    try:
        profile = Profile.objects.get(user=user)
        if profile.role == 'citizen':
            return redirect('citizen_dashboard')
        elif profile.role == 'policymaker':
            return redirect('policymaker_dashboard')
        elif profile.role == 'corporate_leader':
            return redirect('corporate_dashboard')
    except Profile.DoesNotExist:
        pass
    return redirect('home')


def admin_signin(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_overview')
        else:
            error = "Only admin can log in here."

    return render(request, "authentication/admin_signin.html", {'error': error})


@login_required(login_url='signin')
def citizen_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'citizen':
            return redirect_by_role(request.user)
    except Profile.DoesNotExist:
        return redirect('home')

    success = False
    recommendations = []
    comparison = None

    citizen_data, created = CitizenData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        citizen_data.current_city = request.POST.get('current_city')
        citizen_data.preferred_city = request.POST.get('preferred_city')
        citizen_data.job_sector = request.POST.get('job_sector')
        citizen_data.salary_range = request.POST.get('salary_range')

        commute_time = request.POST.get('commute_time')
        citizen_data.commute_time = int(commute_time) if commute_time else None

        citizen_data.transport_mode = request.POST.get('transport_mode')
        citizen_data.housing_priority = request.POST.get('housing_priority')
        citizen_data.health_priority = request.POST.get('health_priority')
        citizen_data.education_priority = request.POST.get('education_priority')
        citizen_data.cost_priority = request.POST.get('cost_priority')
        citizen_data.additional_notes = request.POST.get('additional_notes')

        citizen_data.save()
        success = True

    if citizen_data.current_city:
        recommendations = get_city_recommendations(citizen_data)
        comparison = get_best_city_comparison(citizen_data)

    return render(request, "authentication/citizen_dashboard.html", {
        'citizen_data': citizen_data,
        'success': success,
        'recommendations': recommendations,
        'comparison': comparison,
    })


@login_required(login_url='signin')
def policymaker_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'policymaker':
            return redirect_by_role(request.user)
    except Profile.DoesNotExist:
        return redirect('home')

    success = False
    policymaker_data, created = PolicymakerData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        policymaker_data.target_city = request.POST.get('target_city')
        policymaker_data.policy_focus = request.POST.get('policy_focus')
        policymaker_data.migration_trend = request.POST.get('migration_trend')
        policymaker_data.infrastructure_pressure = request.POST.get('infrastructure_pressure')
        policymaker_data.housing_status = request.POST.get('housing_status')
        policymaker_data.transport_status = request.POST.get('transport_status')
        policymaker_data.employment_status = request.POST.get('employment_status')
        policymaker_data.environmental_status = request.POST.get('environmental_status')
        policymaker_data.budget_level = request.POST.get('budget_level')
        policymaker_data.policy_notes = request.POST.get('policy_notes')

        policymaker_data.save()
        success = True

    responses = SurveyResponse.objects.all()
    total_responses = responses.count()

    def percent(count):
        if total_responses == 0:
            return 0
        return round((count / total_responses) * 100, 1)

    traffic_count = 0
    pollution_count = 0
    job_count = 0
    high_cost_count = 0

    cleaner_air_count = 0
    lower_cost_count = 0
    better_education_count = 0
    better_healthcare_count = 0
    shorter_commute_count = 0

    very_likely_count = 0
    possibly_count = 0
    not_sure_count = 0

    problem_counter = Counter()
    reason_counter = Counter()
    likelihood_counter = Counter()

    for response in responses:
        problems = (response.current_city_problems or "").lower()
        reasons = (response.relocation_reasons or "").lower()
        likelihood = (response.relocation_likelihood or "").lower()

        if "traffic" in problems or "ট্রাফিক" in problems:
            traffic_count += 1
            problem_counter["Traffic Congestion"] += 1

        if "pollution" in problems or "দূষণ" in problems:
            pollution_count += 1
            problem_counter["Pollution"] += 1

        if "job" in problems or "চাকরি" in problems:
            job_count += 1
            problem_counter["Job Opportunities"] += 1

        if "cost" in problems or "living" in problems or "খরচ" in problems or "জীবিক" in problems:
            high_cost_count += 1
            problem_counter["High Living Cost"] += 1

        if "cleaner air" in reasons or "পরিষ্কার বাতাস" in reasons:
            cleaner_air_count += 1
            reason_counter["Cleaner Air"] += 1

        if "lower living cost" in reasons or "কম জীবনযাত্রার ব্যয়" in reasons:
            lower_cost_count += 1
            reason_counter["Lower Living Cost"] += 1

        if "better schools" in reasons or "better education" in reasons or "ভালো স্কুল" in reasons or "বিশ্ববিদ্যালয়" in reasons:
            better_education_count += 1
            reason_counter["Better Education"] += 1

        if "better healthcare" in reasons or "স্বাস্থ্যসেবা" in reasons:
            better_healthcare_count += 1
            reason_counter["Better Healthcare"] += 1

        if "shorter commute" in reasons or "ছোট যাতায়াত" in reasons:
            shorter_commute_count += 1
            reason_counter["Shorter Commute"] += 1

        if "very likely" in likelihood or "খুব সম্ভব" in likelihood:
            very_likely_count += 1
            likelihood_counter["Very Likely"] += 1
        elif "possibly" in likelihood or "সম্ভবত" in likelihood:
            possibly_count += 1
            likelihood_counter["Possibly"] += 1
        elif "not sure" in likelihood or "নিশ্চিত নই" in likelihood:
            not_sure_count += 1
            likelihood_counter["Not Sure"] += 1

    survey_insights = {
        "traffic_problem_percent": percent(traffic_count),
        "pollution_problem_percent": percent(pollution_count),
        "job_problem_percent": percent(job_count),
        "high_cost_problem_percent": percent(high_cost_count),

        "cleaner_air_move_percent": percent(cleaner_air_count),
        "lower_cost_move_percent": percent(lower_cost_count),
        "better_education_move_percent": percent(better_education_count),
        "better_healthcare_move_percent": percent(better_healthcare_count),
        "shorter_commute_move_percent": percent(shorter_commute_count),

        "very_likely_relocate_percent": percent(very_likely_count),
        "possibly_relocate_percent": percent(possibly_count),
        "not_sure_relocate_percent": percent(not_sure_count),
    }

    top_problem = problem_counter.most_common(1)[0][0] if problem_counter else "No data"
    top_reason = reason_counter.most_common(1)[0][0] if reason_counter else "No data"
    top_likelihood = likelihood_counter.most_common(1)[0][0] if likelihood_counter else "No data"

    policy_summary = [
        f"Most reported urban problem: {top_problem}.",
        f"Strongest relocation motivator: {top_reason}.",
        f"Most common relocation response: {top_likelihood}.",
        f"Total survey responses analyzed: {total_responses}."
    ]

    return render(request, "authentication/policymaker_dashboard.html", {
        'policymaker_data': policymaker_data,
        'success': success,
        'survey_insights': survey_insights,
        'policy_summary': policy_summary,
        'total_survey_responses': total_responses,
        'top_problem': top_problem,
        'top_reason': top_reason,
        'top_likelihood': top_likelihood,
    })


@login_required(login_url='signin')
def corporate_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'corporate_leader':
            return redirect_by_role(request.user)
    except Profile.DoesNotExist:
        return redirect('home')

    success = False
    city_comparison = None
    predicted_city = None
    ml_comparison = None
    live_data = None
    live_error = None
    corporate_live_summary = []
    top_city_recommendations = []
    corporate_data, created = CorporateData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        corporate_data.company_name = request.POST.get('company_name')
        corporate_data.business_sector = request.POST.get('business_sector')
        corporate_data.current_city = request.POST.get('current_city')
        corporate_data.target_city = request.POST.get('target_city')

        employee_count = request.POST.get('employee_count')
        corporate_data.employee_count = int(employee_count) if employee_count else None

        corporate_data.office_cost_level = request.POST.get('office_cost_level')
        corporate_data.talent_availability = request.POST.get('talent_availability')
        corporate_data.infrastructure_quality = request.POST.get('infrastructure_quality')
        corporate_data.business_growth_status = request.POST.get('business_growth_status')
        corporate_data.relocation_interest = request.POST.get('relocation_interest')
        corporate_data.corporate_notes = request.POST.get('corporate_notes')

        corporate_data.save()
        success = True

        try:
            predicted_city = predict_city(corporate_data)
            print("Predicted city:", predicted_city)
        except Exception as e:
            print("ML ERROR:", e)
            predicted_city = None




    if corporate_data.current_city and corporate_data.target_city:
        try:
            current_city_data = CityData.objects.get(city_name__iexact=corporate_data.current_city)
            target_city_data = CityData.objects.get(city_name__iexact=corporate_data.target_city)

            rent_difference = current_city_data.avg_monthly_rent - target_city_data.avg_monthly_rent
            commute_difference = current_city_data.avg_commute_minutes - target_city_data.avg_commute_minutes

            city_comparison = {
                "current_city": current_city_data.city_name,
                "target_city": target_city_data.city_name,
                "current_rent": current_city_data.avg_monthly_rent,
                "target_rent": target_city_data.avg_monthly_rent,
                "rent_saving": max(rent_difference, 0),
                "current_commute": current_city_data.avg_commute_minutes,
                "target_commute": target_city_data.avg_commute_minutes,
                "commute_saving": max(commute_difference, 0),
                "current_job_score": current_city_data.job_opportunity_score,
                "target_job_score": target_city_data.job_opportunity_score,
                "current_remote_score": current_city_data.remote_work_score,
                "target_remote_score": target_city_data.remote_work_score,
                "current_traffic_score": current_city_data.traffic_score,
                "target_traffic_score": target_city_data.traffic_score,
            }
        except CityData.DoesNotExist:
            city_comparison = None

    if corporate_data.current_city and predicted_city:
        try:
            current_city_data = CityData.objects.get(city_name__iexact=corporate_data.current_city)
            predicted_city_data = CityData.objects.get(city_name__iexact=predicted_city)

            rent_difference = current_city_data.avg_monthly_rent - predicted_city_data.avg_monthly_rent
            commute_difference = current_city_data.avg_commute_minutes - predicted_city_data.avg_commute_minutes

            ml_comparison = {
                "current_city": current_city_data.city_name,
                "predicted_city": predicted_city_data.city_name,
                "current_rent": current_city_data.avg_monthly_rent,
                "predicted_rent": predicted_city_data.avg_monthly_rent,
                "rent_saving": max(rent_difference, 0),
                "current_commute": current_city_data.avg_commute_minutes,
                "predicted_commute": predicted_city_data.avg_commute_minutes,
                "commute_saving": max(commute_difference, 0),
                "current_job_score": current_city_data.job_opportunity_score,
                "predicted_job_score": predicted_city_data.job_opportunity_score,
                "current_remote_score": current_city_data.remote_work_score,
                "predicted_remote_score": predicted_city_data.remote_work_score,
                "current_traffic_score": current_city_data.traffic_score,
                "predicted_traffic_score": predicted_city_data.traffic_score,
            }
        except CityData.DoesNotExist:
            ml_comparison = None
    if corporate_data.target_city:
      try:
          coords = get_city_coordinates(corporate_data.target_city)

          if coords:
            weather_data = get_live_weather(coords["lat"], coords["lon"])

            live_data = {
                "city": coords["name"],
                "weather": weather_data,
            }
          else:
            live_error = "Could not find coordinates for the target city."

      except Exception as e:
        live_error = str(e) 

    if live_data:
       weather = live_data["weather"]

       if weather.get("temperature") is not None:
               corporate_live_summary.append(
                   f"Current temperature in {live_data['city']} is {weather.get('temperature')}°C."
             )

       if weather.get("weather"):
            corporate_live_summary.append(
               f"Weather condition is currently {weather.get('weather')}."
        )

       if weather.get("humidity") is not None:
            if weather["humidity"] > 80:
                corporate_live_summary.append(
                    "Humidity is quite high, which may affect comfort and operations."
            )
            else:
              corporate_live_summary.append(
                "Humidity level is currently manageable."
            )

       if ml_comparison and ml_comparison.get("rent_saving", 0) > 0:
            corporate_live_summary.append(
                 f"The predicted city may reduce rent cost by {ml_comparison['rent_saving']}."
        ) 
    if corporate_data.current_city:
       try:
           top_city_recommendations = get_top_divisional_city_recommendations(corporate_data)
       except Exception as e:
           print("TOP CITY RECOMMENDATION ERROR:", e)
           top_city_recommendations = []       

    return render(request, "authentication/corporate_dashboard.html", {
    'corporate_data': corporate_data,
    'success': success,
    'city_comparison': city_comparison,
    'predicted_city': predicted_city,
    'ml_comparison': ml_comparison,
    'live_data': live_data,
    'live_error': live_error,
    'corporate_live_summary': corporate_live_summary,
    'top_city_recommendations': top_city_recommendations,
})


@login_required(login_url='signin')
def admin_overview(request):
    if not request.user.is_superuser:
        return HttpResponse("You are not allowed to access this page.")

    total_users = User.objects.count()
    total_citizens = Profile.objects.filter(role='citizen').count()
    total_policymakers = Profile.objects.filter(role='policymaker').count()
    total_corporates = Profile.objects.filter(role='corporate_leader').count()

    citizen_forms = CitizenData.objects.count()
    policymaker_forms = PolicymakerData.objects.count()
    corporate_forms = CorporateData.objects.count()

    recent_users = User.objects.order_by('-date_joined')[:5]

    survey_responses = SurveyResponse.objects.all()
    total_survey_responses = survey_responses.count()
    english_responses = survey_responses.filter(source_language='english').count()
    bangla_responses = survey_responses.filter(source_language='bangla').count()

    problem_counter = Counter()
    reason_counter = Counter()
    likelihood_counter = Counter()

    for response in survey_responses:
        problems = (response.current_city_problems or "").lower()
        reasons = (response.relocation_reasons or "").lower()
        likelihood = (response.relocation_likelihood or "").lower()

        if "traffic" in problems or "ট্রাফিক" in problems:
            problem_counter["Traffic Congestion"] += 1
        if "pollution" in problems or "দূষণ" in problems:
            problem_counter["Pollution"] += 1
        if "job" in problems or "চাকরি" in problems:
            problem_counter["Job Opportunities"] += 1
        if "cost" in problems or "living" in problems or "খরচ" in problems or "জীবিক" in problems:
            problem_counter["High Living Cost"] += 1

        if "cleaner air" in reasons or "পরিষ্কার বাতাস" in reasons:
            reason_counter["Cleaner Air"] += 1
        if "lower living cost" in reasons or "কম জীবনযাত্রার ব্যয়" in reasons:
            reason_counter["Lower Living Cost"] += 1
        if "better schools" in reasons or "better education" in reasons or "ভালো স্কুল" in reasons or "বিশ্ববিদ্যালয়" in reasons:
            reason_counter["Better Education"] += 1
        if "better healthcare" in reasons or "স্বাস্থ্যসেবা" in reasons:
            reason_counter["Better Healthcare"] += 1
        if "shorter commute" in reasons or "ছোট যাতায়াত" in reasons:
            reason_counter["Shorter Commute"] += 1

        if "very likely" in likelihood or "খুব সম্ভব" in likelihood:
            likelihood_counter["Very Likely"] += 1
        elif "possibly" in likelihood or "সম্ভবত" in likelihood:
            likelihood_counter["Possibly"] += 1
        elif "not sure" in likelihood or "নিশ্চিত নই" in likelihood:
            likelihood_counter["Not Sure"] += 1

    most_common_problem = problem_counter.most_common(1)[0][0] if problem_counter else "No data"
    top_relocation_reason = reason_counter.most_common(1)[0][0] if reason_counter else "No data"
    most_common_likelihood = likelihood_counter.most_common(1)[0][0] if likelihood_counter else "No data"

    context = {
        'total_users': total_users,
        'total_citizens': total_citizens,
        'total_policymakers': total_policymakers,
        'total_corporates': total_corporates,
        'citizen_forms': citizen_forms,
        'policymaker_forms': policymaker_forms,
        'corporate_forms': corporate_forms,
        'recent_users': recent_users,

        'total_survey_responses': total_survey_responses,
        'english_responses': english_responses,
        'bangla_responses': bangla_responses,
        'most_common_problem': most_common_problem,
        'top_relocation_reason': top_relocation_reason,
        'most_common_likelihood': most_common_likelihood,
    }

    return render(request, "authentication/admin_overview.html", context)




@csrf_exempt
@require_POST
def project_chatbot(request):
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse({"reply": "Please ask a question."}, status=400)
        print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return JsonResponse(
                {"reply": "Server error: GEMINI_API_KEY is not set."},
                status=500
            )

        client = genai.Client(api_key=api_key)

        system_prompt = """
You are a chatbot for this project website.

Answer only questions related to this project.
This project includes urban analysis, city comparison, policymaker insights,
citizen recommendations, and corporate relocation support.

If the user asks something unrelated, reply exactly:
Sorry, I can only answer questions related to this project.

Keep answers short, clear, and helpful.
"""

        prompt = f"{system_prompt}\n\nUser question: {user_message}"

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )

        return JsonResponse({"reply": response.text})

    except Exception as e:
        return JsonResponse({"reply": f"Error: {str(e)}"}, status=500)