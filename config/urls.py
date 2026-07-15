from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import logout


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


urlpatterns = [
    path("", home_redirect, name="home"),

    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("prediction/", include("apps.prediction.urls")),
    path("remedy/", include("apps.remedy.urls")),
    path("report/", include("apps.report_summarizer.urls")),
    path("prescription/", include("apps.prescription.urls")),
    path("assistant/", include("apps.assistant.urls")),
]

