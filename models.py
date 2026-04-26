from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('citizen', 'Citizen'),
        ('policymaker', 'Policymaker'),
        ('corporate_leader', 'Corporate Leader'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class CitizenData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    current_city = models.CharField(max_length=100)
    preferred_city = models.CharField(max_length=100, blank=True, null=True)
    job_sector = models.CharField(max_length=100, blank=True, null=True)
    salary_range = models.CharField(max_length=50, blank=True, null=True)
    commute_time = models.PositiveIntegerField(blank=True, null=True)
    transport_mode = models.CharField(max_length=50, blank=True, null=True)
    housing_priority = models.CharField(max_length=20, blank=True, null=True)
    health_priority = models.CharField(max_length=20, blank=True, null=True)
    education_priority = models.CharField(max_length=20, blank=True, null=True)
    cost_priority = models.CharField(max_length=20, blank=True, null=True)
    additional_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Citizen Data - {self.user.username}"

class CityData(models.Model):
    city_name = models.CharField(max_length=100, unique=True)

    living_cost_score = models.FloatField()
    traffic_score = models.FloatField()
    air_quality_score = models.FloatField()
    healthcare_score = models.FloatField()
    education_score = models.FloatField()
    job_opportunity_score = models.FloatField()
    remote_work_score = models.FloatField()

    avg_monthly_rent = models.PositiveIntegerField(default=0)
    avg_commute_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.city_name

class PolicymakerData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    target_city = models.CharField(max_length=100)
    policy_focus = models.CharField(max_length=100, blank=True, null=True)
    migration_trend = models.CharField(max_length=50, blank=True, null=True)
    infrastructure_pressure = models.CharField(max_length=50, blank=True, null=True)
    housing_status = models.CharField(max_length=50, blank=True, null=True)
    transport_status = models.CharField(max_length=50, blank=True, null=True)
    employment_status = models.CharField(max_length=50, blank=True, null=True)
    environmental_status = models.CharField(max_length=50, blank=True, null=True)
    budget_level = models.CharField(max_length=50, blank=True, null=True)
    policy_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Policymaker Data - {self.user.username}"


class CorporateData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    company_name = models.CharField(max_length=150)
    business_sector = models.CharField(max_length=100, blank=True, null=True)
    current_city = models.CharField(max_length=100, blank=True, null=True)
    target_city = models.CharField(max_length=100, blank=True, null=True)
    employee_count = models.PositiveIntegerField(blank=True, null=True)
    office_cost_level = models.CharField(max_length=50, blank=True, null=True)
    talent_availability = models.CharField(max_length=50, blank=True, null=True)
    infrastructure_quality = models.CharField(max_length=50, blank=True, null=True)
    business_growth_status = models.CharField(max_length=50, blank=True, null=True)
    relocation_interest = models.CharField(max_length=50, blank=True, null=True)
    corporate_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Corporate Data - {self.user.username}"

class SurveyResponse(models.Model):
    source_language = models.CharField(max_length=20, default='english')
    timestamp = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    city_type = models.CharField(max_length=200, blank=True, null=True)
    job_sector = models.CharField(max_length=200, blank=True, null=True)
    commute_time = models.CharField(max_length=200, blank=True, null=True)
    travel_mode = models.CharField(max_length=200, blank=True, null=True)
    largest_expense = models.CharField(max_length=200, blank=True, null=True)
    affordability = models.CharField(max_length=200, blank=True, null=True)
    education_importance = models.CharField(max_length=200, blank=True, null=True)
    school_relocation_feasibility = models.CharField(max_length=200, blank=True, null=True)

    relocation_reasons = models.TextField(blank=True, null=True)
    current_city_problems = models.TextField(blank=True, null=True)
    relocation_likelihood = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.source_language} survey - {self.email or 'anonymous'}"