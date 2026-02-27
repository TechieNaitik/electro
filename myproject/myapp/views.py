import re, random, time, secrets
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.conf import settings
from django.db.models.functions import Lower

from .models import Customer, Category, Product

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────────────────────────────────────
def home(request):
    context = {
        'categories': Category.objects.all(),
        'products': Product.objects.all(),
    }
    return render(request, 'index.html', context)

def index(request):
    context = {
        'categories': Category.objects.all(),
        'products': Product.objects.all(),
    }
    return render(request, 'index.html', context)

def category_products(request, cid):
    context = {
        'categories': Category.objects.all(),
    }
    if cid == 0:
        context['products'] = Product.objects.all()
    else:
        category = Category.objects.get(id=cid)
        context['products'] = Product.objects.filter(category_id=category)
        context['selected_category'] = category
    
    return render(request, 'index.html', context)

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
            return render(request, 'register.html', {'categories': Category.objects.all(), 'form_data': {'name': name, 'email': email}})

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html', {'categories': Category.objects.all(), 'form_data': {'name': name, 'email': email}})

        if Customer.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'register.html', {'categories': Category.objects.all(), 'form_data': {'name': name}})

        Customer.objects.create(full_name=name, email=email, password=password)
        
        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')

    return render(request, 'register.html', {'categories': Category.objects.all()})

def login(request):
    if 'email' in request.session:
        return redirect('home')

    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, 'login.html', {'categories': Category.objects.all()})
        
        if not password:
            messages.error(request, "Please enter your password.")
            return render(request, 'login.html', {'categories': Category.objects.all()})

        customer = Customer.objects.filter(email=email).first()
        
        if customer and customer.password == password:
            request.session['email'] = customer.email
            request.session['name'] = customer.full_name
            request.session.set_expiry(0)
            messages.success(request, f"Welcome back, {customer.full_name}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, 'login.html', {'categories': Category.objects.all()})

    return render(request, 'login.html', {'categories': Category.objects.all()})

def shop(request, cid=0):
    context = {
        'categories': Category.objects.all(),
    }
    
    # Get category ID from GET if not in URL
    get_cid = request.GET.get('cid')
    if get_cid:
        try:
            cid = int(get_cid)
        except ValueError:
            pass

    # Get initial products based on category
    if cid == 0:
        products = Product.objects.all()
    else:
        try:
            category = Category.objects.get(id=cid)
            products = Product.objects.filter(category_id=category)
            context['selected_category'] = category
        except Category.DoesNotExist:
            products = Product.objects.all()

    # Apply search query if present
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)
        context['search_query'] = query

    # Apply price filter if present
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
            context['current_max_price'] = max_price
        except ValueError:
            pass

    # Apply sorting (default: Name A-Z, case-insensitive, lowercase before uppercase)
    sort = request.GET.get('sort', 'Name, A-Z')
    # Annotate with lower_name for case-insensitive comparison
    products = products.annotate(lower_name=Lower('name'))
    # sort_map: tuples of ORM order fields
    # Primary = lower_name (case-insensitive alpha), secondary = -name (lowercase before uppercase)
    sort_map = {
        'Name, A-Z':   ('lower_name', '-name'),
        'Name, Z-A':   ('-lower_name', '-name'),
        'Price, ASC':  ('price',),
        'Price, DESC': ('-price',),
    }
    order_fields = sort_map.get(sort, ('lower_name', '-name'))
    products = products.order_by(*order_fields)
    context['current_sort'] = sort

    context['products'] = products
    return render(request, 'shop.html', context)

def single(request, pid):
    product = get_object_or_404(Product, pk=pid)
    related_products = Product.objects.filter(
        category_id=product.category_id
    ).exclude(pk=pid)[:3]
    context = {
        'categories': Category.objects.all(),
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'single.html', context)

def cart(request):
    if 'email' not in request.session:
        return redirect('login')
    
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'cart.html', context)

def checkout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'checkout.html', context)

def contact(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'contact.html', context)

def error(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'error.html', context)

def about(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'about.html', context)

def privacy_policy(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'privacy_policy.html', context)

def terms(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'terms.html', context)

def sitemap(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'sitemap.html', context)

def faq(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'faq.html', context)

def bestseller(request):
    context = {
        'categories': Category.objects.all(),
        'products': Product.objects.all(),
    }
    return render(request, 'bestseller.html', context)

def logout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect('login')

def forgot_password(request):    
    if request.method == "POST":
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.all()})
            
        if not Customer.objects.filter(email=email).exists():
            messages.error(request, "No account found with this email.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

        # Clear any existing reset data
        request.session.pop('reset_otp', None)
        request.session.pop('reset_email', None)
        request.session.pop('reset_otp_time', None)

        otp = str(secrets.randbelow(900000) + 100000)

        request.session['reset_otp'] = otp
        request.session['reset_otp_time'] = time.time()
        request.session['reset_email'] = email
        
        try:
            send_mail(
                'Password Reset OTP',
                f'Your OTP for password reset is {otp}. Do not share it with anyone.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success(request, f"An OTP has been sent to {email}.")
            return redirect('reset_password')
        except Exception as e:
            messages.error(request, "Failed to send OTP. Please check email configuration.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

    return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

def reset_password(request):
    reset_email = request.session.get('reset_email')
    
    if not reset_email:
        messages.error(request, "Please request a password reset first.")
        return redirect('forgot_password')
    
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        otp = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not all([email, otp, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'reset_password.html', {'categories': Category.objects.all()})

        if email != reset_email:
            messages.error(request, "Email does not match the one OTP was sent to.")
            return render(request, 'reset_password.html', {'categories': Category.objects.all()})

        if str(otp) != request.session.get('reset_otp'):
            messages.error(request, "Invalid OTP.")
            return render(request, 'reset_password.html', {'categories': Category.objects.all()})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'reset_password.html', {'categories': Category.objects.all()})

        if time.time() - request.session.get('reset_otp_time', 0) > 300:
            messages.error(request, "OTP expired.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

        Customer.objects.filter(email=email).update(password=new_password)
        
        # Clear reset session variables
        if 'reset_otp' in request.session:
            del request.session['reset_otp']
        if 'reset_email' in request.session:
            del request.session['reset_email']
            
        # Log out the user if they were already logged in using the old password
        if request.session.get('email') == email:
            del request.session['email']
            if 'name' in request.session:
                del request.session['name']
            
        messages.success(request, "Your password has been reset successfully! Please log in with your new password.")
        return redirect('login')

    return render(request, 'reset_password.html', {'categories': Category.objects.all()})
