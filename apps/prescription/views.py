from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services.prescription_engine import analyze_prescription


@login_required
def prescription_view(request):
    result = None

    if request.method == "POST":
        uploaded_file = request.FILES.get("prescription")

        manual_text = (
            request.POST.get("prescription_text", "")
            or request.POST.get("corrected_text", "")
        )

        result = analyze_prescription(
            uploaded_file=uploaded_file,
            manual_text=manual_text
        )

    return render(request, "prescription/index.html", {"result": result})