from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .services.remedy_engine import predict_disease


@login_required
def remedy_view(request):

    symptoms = ""

    disease = None
    confidence = None
    severity = None
    remedies = []
    advice = []

    if request.method == "POST":

        symptoms = request.POST.get(
            "symptoms",
            ""
        )

        result = predict_disease(
            symptoms
        )

        disease = result.get(
            "predicted_disease"
        )

        confidence = result.get(
            "confidence"
        )

        severity = result.get(
            "severity"
        )

        remedies = result.get(
            "remedies",
            []
        )

        advice = result.get(
            "advice",
            []
        )

    context = {

        "symptoms": symptoms,

        "disease": disease,

        "confidence": confidence,

        "severity": severity,

        "remedies": remedies,

        "advice": advice

    }

    return render(

        request,

        "remedy/index.html",

        context

    )