from django.urls import path
from .views import prescription_view

urlpatterns = [
    path("", prescription_view, name="prescription"),
]