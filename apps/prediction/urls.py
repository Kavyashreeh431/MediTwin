from django.urls import path
from .views import create_profile, update_profile, health_summary

urlpatterns = [
    path("", create_profile, name="health_profile"),
    path("update/", update_profile, name="update_health_profile"),
    path("summary/", health_summary, name="health_summary"),
]