from django.urls import path
from .views import assistant_view, clear_chat_view

urlpatterns = [
    path("", assistant_view, name="assistant"),
    path("clear/", clear_chat_view, name="clear_assistant_chat"),
]