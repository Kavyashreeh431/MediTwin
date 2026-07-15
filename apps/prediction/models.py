from django.db import models
from django.contrib.auth.models import User


class HealthProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    age = models.IntegerField()

    gender = models.CharField(
        max_length=20
    )

    height = models.FloatField()

    weight = models.FloatField()

    bmi = models.FloatField(
        null=True
    )

    blood_pressure = models.CharField(
        max_length=20
    )

    glucose = models.FloatField()

    heart_rate = models.IntegerField()

    exercise = models.IntegerField()

    sleep_hours = models.FloatField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.username