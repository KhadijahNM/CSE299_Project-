from django.contrib import admin
from .models import Profile, CitizenData, PolicymakerData, CorporateData, CityData, SurveyResponse

admin.site.register(Profile)
admin.site.register(CitizenData)
admin.site.register(PolicymakerData)
admin.site.register(CorporateData)
admin.site.register(CityData)
admin.site.register(SurveyResponse)
