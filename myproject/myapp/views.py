import re
from django.contrib import messages
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

def index(request):
    return render(request, 'index.html')

def register(request):
    if 'email' in request.session:
        return redirect('home')

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not all([name, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'register.html', {'form_data': {'name': name, 'email': email}})

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
    if 'email' in request.session:
        return redirect('home')

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
            request.session['email'] = customer.email
            request.session['name'] = customer.full_name
            request.session.set_expiry(0)
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
    if 'email' not in request.session:
        return redirect('login')
    
    return render(request, 'cart.html')

def checkout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    return render(request, 'checkout.html')

def contact(request):
    return render(request, 'contact.html')

def error(request):
    return render(request, 'error.html')

def bestseller(request):
    return render(request, 'bestseller.html')

def logout(request):
    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect('login')

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, 'forgot_password.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'forgot_password.html')

        # Here you would generate and send the OTP to the user's email
        # For demonstration purposes, we'll just display a success message
        messages.success(request, f"An OTP has been sent to {email}.")
        return redirect('reset_password')

    return render(request, 'forgot_password.html')

def reset_password(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        otp = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not all([email, otp, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'reset_password.html')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'reset_password.html')

        # Here you would verify the OTP and update the user's password
        # For demonstration purposes, we'll just display a success message
        Customer.objects.filter(email=email).update(password=new_password)
        messages.success(request, "Your password has been reset successfully!")
        return redirect('login')

    return render(request, 'reset_password.html')