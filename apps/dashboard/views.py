from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.prediction.models import HealthProfile
from apps.prediction.services.shap_engine import HealthTwin


@login_required
def dashboard(request):
    health_profile = HealthProfile.objects.filter(
        user=request.user
    ).first()

    risk = None
    health_score = None
    prediction_confidence = None
    recommendation = None
    bmi_status = None

    user_highlight_title = "Create your health profile"
    user_highlight_message = "Start your first health check to get personalized AI health insights."

    attention_factors = []
    good_factors = []
    shap_values = []

    health_chart_labels = []
    health_chart_values = []

    feature_chart_labels = []
    feature_chart_values = []

    report_chart_labels = []
    report_chart_values = []

    if health_profile:
        if health_profile.height and health_profile.weight:
            health_profile.bmi = round(
                health_profile.weight / ((health_profile.height / 100) ** 2),
                2
            )
            health_profile.save()

        if not health_profile.bmi:
            bmi_status = "Not calculated"
        elif health_profile.bmi < 18.5:
            bmi_status = "Underweight"
        elif health_profile.bmi < 25:
            bmi_status = "Normal"
        elif health_profile.bmi < 30:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obesity"

        twin = HealthTwin(health_profile)
        result = twin.explain()

        risk = result.get("risk", "Low")
        health_score = result.get("health_score", 50)
        prediction_confidence = result.get("confidence", 50)
        recommendation = result.get(
            "recommendation",
            "Maintain a healthy lifestyle and consult a doctor for medical advice."
        )

        shap_values = result.get("shap_values", [])

        for item in shap_values:
            feature = item.get("feature", "")
            status = item.get("status", "")
            reason = item.get("reason", "")
            impact = item.get("impact", 0)

            if status == "Negative":
                attention_factors.append({
                    "feature": feature,
                    "reason": reason
                })
                feature_chart_values.append(-abs(impact))
            else:
                good_factors.append({
                    "feature": feature,
                    "reason": reason
                })
                feature_chart_values.append(abs(impact))

            feature_chart_labels.append(feature)

        if risk == "High":
            user_highlight_title = "Your health needs attention"
            user_highlight_message = "Several indicators may need improvement. Please review your health summary carefully."
        elif risk == "Moderate":
            user_highlight_title = "Some indicators need attention"
            user_highlight_message = "Your overall health is fair, but one or more values need improvement."
        else:
            user_highlight_title = "Good health indicators"
            user_highlight_message = "Most of your entered health values are within a healthy range."

        health_chart_labels = [
            "BMI",
            "Glucose",
            "Heart Rate",
            "Sleep Hours"
        ]

        health_chart_values = [
            float(health_profile.bmi or 0),
            float(health_profile.glucose or 0),
            float(health_profile.heart_rate or 0),
            float(health_profile.sleep_hours or 0),
        ]

        if hasattr(health_profile, "exercise") and health_profile.exercise is not None:
            health_chart_labels.append("Exercise")
            health_chart_values.append(float(health_profile.exercise or 0))

    return render(
        request,
        "dashboard/home.html",
        {
            "health_profile": health_profile,
            "risk": risk,
            "health_score": health_score,
            "prediction_confidence": prediction_confidence,
            "recommendation": recommendation,
            "bmi_status": bmi_status,
            "user_highlight_title": user_highlight_title,
            "user_highlight_message": user_highlight_message,
            "attention_factors": attention_factors,
            "good_factors": good_factors,

            "health_chart_labels": health_chart_labels,
            "health_chart_values": health_chart_values,
            "feature_chart_labels": feature_chart_labels,
            "feature_chart_values": feature_chart_values,

            "report_chart_labels": report_chart_labels,
            "report_chart_values": report_chart_values,
        }
    )