from django.db import models
from django.contrib.auth.models import User


class RemedyRequest(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    symptoms = models.TextField()

    predicted_disease = models.CharField(
        max_length=200,
        blank=True
    )

    recommendation = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.username