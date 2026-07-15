from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import HealthProfile
from .forms import HealthProfileForm
from .services.shap_engine import HealthTwin


@login_required
def create_profile(request):
    existing_profile = HealthProfile.objects.filter(
        user=request.user
    ).first()

    if request.method == "POST":
        form = HealthProfileForm(
            request.POST,
            instance=existing_profile
        )

        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user

            if profile.height and profile.weight:
                height_m = profile.height / 100
                profile.bmi = round(
                    profile.weight / (height_m ** 2),
                    2
                )

            profile.save()
            return redirect("health_summary")

    else:
        # Fresh empty form when user opens Health Predictor
        form = HealthProfileForm()

    return render(
        request,
        "prediction/profile_form.html",
        {
            "form": form,
            "is_update": False
        }
    )


@login_required
def update_profile(request):
    profile = HealthProfile.objects.filter(
        user=request.user
    ).first()

    if not profile:
        return redirect("health_profile")

    if request.method == "POST":
        form = HealthProfileForm(
            request.POST,
            instance=profile
        )

        if form.is_valid():
            updated_profile = form.save(commit=False)
            updated_profile.user = request.user

            if updated_profile.height and updated_profile.weight:
                height_m = updated_profile.height / 100
                updated_profile.bmi = round(
                    updated_profile.weight / (height_m ** 2),
                    2
                )

            updated_profile.save()
            return redirect("health_summary")

    else:
        # Update page shows existing values
        form = HealthProfileForm(instance=profile)

    return render(
        request,
        "prediction/profile_form.html",
        {
            "form": form,
            "is_update": True
        }
    )


@login_required
def health_summary(request):
    profile = HealthProfile.objects.filter(
        user=request.user
    ).first()

    if not profile:
        return redirect("health_profile")

    if profile.height and profile.weight:
        profile.bmi = round(
            profile.weight / ((profile.height / 100) ** 2),
            2
        )
        profile.save()

    if not profile.bmi:
        bmi_status = "Not calculated"
    elif profile.bmi < 18.5:
        bmi_status = "Underweight"
    elif profile.bmi < 25:
        bmi_status = "Normal"
    elif profile.bmi < 30:
        bmi_status = "Overweight"
    else:
        bmi_status = "Obesity"

    twin = HealthTwin(profile)
    result = twin.explain()

    context = {
        "profile": profile,
        "risk": result.get("risk", "Low"),
        "health_score": result.get("health_score", 50),
        "prediction_confidence": result.get("confidence", 50),
        "shap_values": result.get("shap_values", []),
        "summary": result.get("summary", "No summary available."),
        "bmi_status": bmi_status,
        "recommendation": result.get(
            "recommendation",
            "Maintain a healthy lifestyle and consult a doctor for medical advice."
        ),
    }

    return render(
        request,
        "prediction/summary.html",
        context
    )