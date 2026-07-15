from django import forms
from .models import HealthProfile


class HealthProfileForm(forms.ModelForm):

    class Meta:

        model = HealthProfile

        exclude = (
            "user",
            "bmi",
        )