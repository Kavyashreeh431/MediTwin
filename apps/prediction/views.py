from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import HealthProfile
from .forms import HealthProfileForm


@login_required
def create_profile(request):
    
    if request.method == "POST":

        form = HealthProfileForm(
            request.POST
        )

        if form.is_valid():

            profile = form.save(
                commit=False
            )

            profile.user = request.user

            height_m = (
                profile.height / 100
            )

            profile.bmi = (
                profile.weight /
                (
                    height_m ** 2
                )
            )

            profile.save()

            return redirect(
                "dashboard"
            )

    else:

        form = HealthProfileForm()

    return render(
        request,
        "prediction/profile_form.html",
        {
            "form": form
        }
    )

@login_required
def health_summary(request):

    profile = HealthProfile.objects.filter(
        user=request.user
    ).last()

    if not profile:

        return redirect(
            "health-profile"
        )

    bmi_status = ""

    if profile.bmi < 18.5:
        bmi_status = "Underweight"

    elif profile.bmi < 25:
        bmi_status = "Normal"

    elif profile.bmi < 30:
        bmi_status = "Overweight"

    else:
        bmi_status = "Obesity"

    risk_score = 0
    explanations = []


    if profile.glucose > 140:

        risk_score += 1

        explanations.append(
            "High glucose level"
        )


    if profile.heart_rate > 100:

        risk_score += 1

        explanations.append(
            "Elevated heart rate"
        )


    if profile.sleep_hours < 6:

        risk_score += 1

        explanations.append(
            "Low sleep duration"
        )


    if profile.bmi >= 30:

        risk_score += 1

        explanations.append(
            "High BMI"
        )


    if risk_score <= 1:

        risk = "Low"

    elif risk_score <= 2:

        risk = "Moderate"

    else:

        risk = "High"
    context = {

    "profile": profile,

    "risk": risk,

    "bmi_status": bmi_status,

    "explanations": explanations,

    "health_score": max(
        100 - (risk_score * 20),
        20
    ),

    "prediction_confidence": 85
}

    return render(
        request,
        "prediction/summary.html",
        context
    )