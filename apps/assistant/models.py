from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assistant_messages"
    )

    question = models.TextField()
    answer = models.TextField()

    intent = models.CharField(
        max_length=80,
        blank=True
    )

    topic = models.CharField(
        max_length=120,
        blank=True
    )

    safety_level = models.CharField(
        max_length=30,
        default="normal"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]