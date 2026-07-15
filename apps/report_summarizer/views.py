from django.shortcuts import render
from .services.extractor import extract_pdf_text
from .services.summarizer import summarize


def upload_report(request):

    summary = None
    extracted = None
    error = None

    if request.method == "POST":

        print("\nPOST RECEIVED")

        report = request.FILES.get("report")

        print("FILE:", report)

        if report:

            extracted = extract_pdf_text(report)

            print("EXTRACTED:")
            print(extracted)

            summary = summarize(extracted)

            print("SUMMARY:")
            print(summary)

        else:
            error = "No file uploaded"

    return render(
        request,
        "report/upload.html",
        {
            "summary": summary,
            "text": extracted,
            "error": error
        }
    )