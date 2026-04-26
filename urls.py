from django.contrib import admin
from django.urls import path,include
from .import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('admin-login/', views.admin_signin, name='admin_signin'),

    path('citizen-dashboard/', views.citizen_dashboard, name='citizen_dashboard'),
    path('policymaker-dashboard/', views.policymaker_dashboard, name='policymaker_dashboard'),
    path('corporate-dashboard/', views.corporate_dashboard, name='corporate_dashboard'),
    path('admin-overview/', views.admin_overview, name='admin_overview'),
    path('api/project-chatbot/', views.project_chatbot, name='project_chatbot'),
]