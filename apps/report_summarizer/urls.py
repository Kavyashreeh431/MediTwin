from django.urls import path
from .views import upload_report

urlpatterns = [
    path("", upload_report, name="report"),
]