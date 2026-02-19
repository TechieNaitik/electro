import re
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect, HttpResponse

from .models import Customer

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────────────────────────────────────
def home(request):
    return render(request, 'index.html')
    return HttpResponse("Welcome to the Home Page!")


def index(request):
    return render(request, 'index.html')

def register(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # 1. Check for empty fields
        if not all([name, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'register.html', {'form_data': {'name': name, 'email': email}})

        # 2. Check password match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html', {'form_data': {'name': name, 'email': email}})

        if Customer.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'register.html', {'form_data': {'name': name}})

        Customer.objects.create(full_name=name, email=email, password=password)
        
        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')

    return render(request, 'register.html')

def login(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, 'login.html')
        
        if not password:
            messages.error(request, "Please enter your password.")
            return render(request, 'login.html')

        customer = Customer.objects.filter(email=email).first()
        
        if customer and customer.password == password:
            messages.success(request, f"Welcome back, {customer.full_name}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, 'login.html')

    return render(request, 'login.html')

def shop(request):
    return render(request, 'shop.html')

def single(request):
    return render(request, 'single.html')

def cart(request):
    return render(request, 'cart.html')

def checkout(request):
    return render(request, 'checkout.html')

def contact(request):
    return render(request, 'contact.html')

def error(request):
    return render(request, 'error.html')

def bestseller(request):
    return render(request, 'bestseller.html')
