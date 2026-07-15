from django.contrib import admin
from .models import RemedyRequest


@admin.register(RemedyRequest)
class RemedyRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "short_symptoms",
        "predicted_disease",
        "confidence",
        "severity",
        "created_at",
    )

    search_fields = (
        "user__username",
        "symptoms",
        "predicted_disease",
        "severity",
    )

    list_filter = (
        "severity",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )

    def short_symptoms(self, obj):
        return obj.symptoms[:60]