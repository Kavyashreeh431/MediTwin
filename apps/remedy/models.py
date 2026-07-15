from django.db import models
from django.contrib.auth.models import User


class RemedyRequest(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="remedy_requests",
        null=True,
        blank=True
    )

    symptoms = models.TextField()
    predicted_disease = models.CharField(max_length=150, blank=True)
    confidence = models.FloatField(default=0)
    severity = models.CharField(max_length=50, blank=True)

    remedies = models.TextField(blank=True)
    advice = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.symptoms[:40]}"