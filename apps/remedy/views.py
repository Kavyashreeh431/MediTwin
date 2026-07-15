from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import RemedyRequest
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
        symptoms = request.POST.get("symptoms", "").strip()

        if symptoms:
            result = predict_disease(symptoms)

            disease = result.get("predicted_disease")
            confidence = result.get("confidence")
            severity = result.get("severity")
            remedies = result.get("remedies", [])
            advice = result.get("advice", [])

            RemedyRequest.objects.create(
                user=request.user,
                symptoms=symptoms,
                predicted_disease=disease or "",
                confidence=float(confidence or 0),
                severity=severity or "",
                remedies="\n".join(remedies) if isinstance(remedies, list) else str(remedies),
                advice="\n".join(advice) if isinstance(advice, list) else str(advice),
            )

    return render(
        request,
        "remedy/index.html",
        {
            "symptoms": symptoms,
            "disease": disease,
            "confidence": confidence,
            "severity": severity,
            "remedies": remedies,
            "advice": advice,
        }
    )