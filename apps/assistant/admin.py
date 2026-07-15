from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "short_question", "created_at")
    search_fields = ("user__username", "question", "answer")
    list_filter = ("created_at",)

    def short_question(self, obj):
        return obj.question[:60]