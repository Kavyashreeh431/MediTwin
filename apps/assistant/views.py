from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import ChatMessage
from .services.assistant_engine import generate_assistant_response


def get_local_datetime(date_time):
    if timezone.is_aware(date_time):
        return timezone.localtime(date_time)
    return date_time


@login_required
def assistant_view(request):
    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if not question:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "error": "Please type a health-related question."
                })

            return redirect("assistant")

        previous_messages = ChatMessage.objects.filter(
            user=request.user
        ).order_by("-created_at")[:6]

        previous_messages = list(reversed(previous_messages))

        chat_history = []

        for message in previous_messages:
            chat_history.append({
                "question": message.question,
                "answer": message.answer
            })

        answer = generate_assistant_response(
            question,
            chat_history=chat_history
        )

        saved_message = ChatMessage.objects.create(
            user=request.user,
            question=question,
            answer=answer
        )

        local_created_at = get_local_datetime(saved_message.created_at)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "question": question,
                "answer": answer,
                "date_key": local_created_at.strftime("%Y-%m-%d"),
                "date_label": local_created_at.strftime("%A, %d %B %Y"),
                "time_label": local_created_at.strftime("%I:%M %p")
            })

        return redirect("assistant")

    chat_messages = ChatMessage.objects.filter(
        user=request.user
    ).order_by("-created_at")[:20]

    chat_messages = list(reversed(chat_messages))

    last_message_date_key = ""

    if chat_messages:
        last_message_datetime = get_local_datetime(chat_messages[-1].created_at)
        last_message_date_key = last_message_datetime.strftime("%Y-%m-%d")

    return render(
        request,
        "assistant/chat.html",
        {
            "chat_messages": chat_messages,
            "last_message_date_key": last_message_date_key
        }
    )


@login_required
def clear_chat_view(request):
    ChatMessage.objects.filter(user=request.user).delete()
    return redirect("assistant")