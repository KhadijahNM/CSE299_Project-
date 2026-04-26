from django.contrib import admin
from .models import (
    City, TrafficData, PollutionData, QoLIndex,
    JobSector, Company, CommuteProfile, PolicySimReport,
    AirQualityReading, CityMetric
)

admin.site.register(City)
admin.site.register(TrafficData)
admin.site.register(PollutionData)
admin.site.register(QoLIndex)
admin.site.register(JobSector)
admin.site.register(Company)
admin.site.register(CommuteProfile)
admin.site.register(PolicySimReport)
admin.site.register(AirQualityReading)
admin.site.register(CityMetric)