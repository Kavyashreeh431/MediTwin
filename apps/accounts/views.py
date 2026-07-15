from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User

from .forms import UserRegisterForm


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not User.objects.filter(username=username).exists():
            messages.error(request, "User does not exist. Please register first.")
            return redirect("login")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid credentials. Please check your username and password.")
        return redirect("login")

    register_form = UserRegisterForm()
    return render(request, "accounts/login.html", {"register_form": register_form})


def register_view(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect("login")

        for error in form.errors.values():
            messages.error(request, error)

        return redirect("login")

    return redirect("login")


def admin_login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            return redirect("/admin/")

        messages.error(request, "Invalid admin credentials or you do not have admin permission.")
        return redirect("admin_login")

    return render(request, "accounts/admin_login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")