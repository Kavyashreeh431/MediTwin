from django.urls import path

from .views import (
    create_profile,
    health_summary,
)


urlpatterns = [

    path(
        "",
        create_profile,
        name="health-profile"
    ),

    path(
        "summary/",
        health_summary,
        name="health-summary"
    ),

]