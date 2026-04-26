from django.db import models
from django.contrib.auth.models import User


# -------------------------
# Existing role/profile models
# -------------------------

class Profile(models.Model):
    ROLE_CHOICES = (
        ("citizen", "Citizen"),
        ("policymaker", "Policymaker"),
        ("corporate_leader", "Corporate Leader"),
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


# -------------------------
# Bangladesh city + metrics tables
# -------------------------

class City(models.Model):
    city_name = models.CharField(max_length=100, unique=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    population = models.IntegerField(blank=True, null=True)
    cost_of_living_index = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    infrastructure_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.city_name
class TrafficData(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="traffic_records")
    avg_commute_time_minutes = models.IntegerField(blank=True, null=True)
    congestion_level = models.CharField(max_length=50, blank=True, null=True)
    daily_delay_minutes = models.IntegerField(blank=True, null=True)

    source = models.CharField(max_length=100, default="unknown")
    last_updated = models.DateTimeField(auto_now=True)
    raw_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Traffic - {self.city.city_name}"

class PollutionData(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="pollution_records")
    pm25 = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    air_quality_level = models.CharField(max_length=50, blank=True, null=True)
    estimated_vehicle_emission = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    source = models.CharField(max_length=100, default="unknown")
    last_updated = models.DateTimeField(auto_now=True)
    raw_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Pollution - {self.city.city_name}"


class QoLIndex(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="qol_records")
    healthcare_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    education_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    safety_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    housing_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    final_qol_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"QoL - {self.city.city_name}"


class JobSector(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="job_sectors")
    sector_name = models.CharField(max_length=100)
    job_count = models.IntegerField(blank=True, null=True)
    avg_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.sector_name} - {self.city.city_name}"


class Company(models.Model):
    RELOCATE_CHOICES = (("yes", "Yes"), ("no", "No"))

    company_name = models.CharField(max_length=100)
    sector = models.ForeignKey(JobSector, on_delete=models.SET_NULL, blank=True, null=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    employee_count = models.IntegerField(blank=True, null=True)
    relocation_possible = models.CharField(max_length=3, choices=RELOCATE_CHOICES, default="no")

    def __str__(self):
        return self.company_name


class CommuteProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    daily_commute_distance_km = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    daily_commute_time_minutes = models.IntegerField(blank=True, null=True)
    transport_mode = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Commute - {self.user.username} - {self.city.city_name}"


class PolicySimReport(models.Model):
    source_city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="policy_reports_source")
    target_city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="policy_reports_target")

    sector_name = models.CharField(max_length=100, blank=True, null=True)
    relocated_jobs = models.IntegerField(blank=True, null=True)
    estimated_traffic_reduction_percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    estimated_pollution_reduction_percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    report_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Policy Report: {self.source_city.city_name} → {self.target_city.city_name}"


# -------------------------
# Step 1.1 (REAL-TIME API storage): raw readings + latest snapshot
# -------------------------

class AirQualityReading(models.Model):
    city_name = models.CharField(max_length=100)
    pm25 = models.FloatField(null=True, blank=True)
    aqi = models.FloatField(null=True, blank=True)

    source = models.CharField(max_length=100, default="unknown")
    fetched_at = models.DateTimeField(auto_now_add=True)

    raw_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.city_name} AQ @ {self.fetched_at}"


class CityMetric(models.Model):
    city_name = models.CharField(max_length=100, unique=True)

    pm25_latest = models.FloatField(null=True, blank=True)
    aqi_latest = models.FloatField(null=True, blank=True)
    traffic_minutes_latest = models.FloatField(null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True)
    aqi_source = models.CharField(max_length=100, default="unknown")
    traffic_source = models.CharField(max_length=100, default="unknown")

    def __str__(self):
        return f"{self.city_name} metrics"


# -------------------------
# Bangladesh-only historical AQI dataset (periodic import / training)
# -------------------------

class HistoricalAQI(models.Model):
    city_name = models.CharField(max_length=100)

    aqi = models.FloatField(null=True, blank=True)
    pm25 = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField()
    source = models.CharField(max_length=150, default="Mendeley Bangladesh AQI 2000–2025")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["city_name", "recorded_at"], name="uniq_city_time")
        ]
        indexes = [
            models.Index(fields=["city_name", "recorded_at"]),
        ]

    def __str__(self):
        return f"{self.city_name} historical AQI @ {self.recorded_at}"
    
class ExternalCitizenSurvey(models.Model):
    current_city = models.CharField(max_length=100, blank=True, null=True)
    preferred_city = models.CharField(max_length=100, blank=True, null=True)
    main_problem = models.TextField(blank=True, null=True)
    relocation_reason = models.TextField(blank=True, null=True)
    raw_data = models.JSONField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.current_city} -> {self.preferred_city}" 