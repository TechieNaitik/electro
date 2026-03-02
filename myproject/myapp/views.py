import re, random, time, secrets
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.db.models.functions import Lower

from .models import Customer, Category, Product, Cart, Order, OrderItem

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

def add_to_cart(request, pid):
    if 'email' not in request.session:
        return redirect('login')
    
    product = get_object_or_404(Product, pk=pid)
    customer = Customer.objects.get(email=request.session['email'])
    
    qty = request.POST.get('qty') or request.GET.get('qty', 1)
    try:
        qty = int(qty)
    except ValueError:
        qty = 1
        
    cart_item = Cart.objects.filter(customer=customer, product=product).first()
    current_qty = cart_item.quantity if cart_item else 0
    
    if product.stock_quantity < current_qty + qty:
        messages.error(request, f"Only {product.stock_quantity} units of {product.name} are available. You already have {current_qty} in cart.")
        return redirect(request.META.get('HTTP_REFERER', 'cart'))

    if cart_item:
        cart_item.quantity += qty
        cart_item.save()
    else:
        cart_item = Cart.objects.create(customer=customer, product=product, quantity=qty)
        
    cart_items = Cart.objects.filter(customer=customer)
    cart_count = sum(item.quantity for item in cart_items)
    cart_total = sum(item.total_price() for item in cart_items)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"{product.name} added to cart.",
            'cart_count': cart_count,
            'cart_total': cart_total
        })

    messages.success(request, f"{product.name} added to cart.")
    return redirect(request.META.get('HTTP_REFERER', 'cart'))

def update_cart(request, cid, action):
    if 'email' not in request.session:
        return redirect('login')
        
    customer = Customer.objects.get(email=request.session['email'])
    cart_item = get_object_or_404(Cart, pk=cid, customer=customer)
    
    if action == 'increase':
        if cart_item.product.stock_quantity > cart_item.quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': f"Only {cart_item.product.stock_quantity} units available."})
            messages.error(request, f"Only {cart_item.product.stock_quantity} units available for {cart_item.product.name}.")
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    elif action == 'remove':
        cart_item.delete()
        
    cart_items = Cart.objects.filter(customer=customer)
    subtotal = sum(item.total_price() for item in cart_items)
    shipping = 15 if subtotal > 0 else 0
    total = subtotal + shipping
    cart_count = sum(item.quantity for item in cart_items)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        item_data = None
        if action != 'remove' and Cart.objects.filter(id=cid).exists():
            item_data = {
                'quantity': cart_item.quantity,
                'total_price': cart_item.total_price()
            }
        return JsonResponse({
            'status': 'success',
            'item': item_data,
            'subtotal': subtotal,
            'shipping': shipping,
            'total': total,
            'cart_count': cart_count,
            'removed': action == 'remove' or not Cart.objects.filter(id=cid).exists()
        })

    return redirect('cart')

def cart(request):
    if 'email' not in request.session:
        return redirect('login')
    
    customer = Customer.objects.get(email=request.session['email'])
    cart_items = Cart.objects.filter(customer=customer)
    
    subtotal = sum(item.total_price() for item in cart_items)
    shipping = 15 if subtotal > 0 else 0
    total = subtotal + shipping
    
    context = {
        'categories': Category.objects.all(),
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'cart.html', context)

def checkout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    customer = Customer.objects.get(email=request.session['email'])
    cart_items = Cart.objects.filter(customer=customer)
    
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart')
        
    subtotal = sum(item.total_price() for item in cart_items)
    shipping = 15 if subtotal > 0 else 0
    total = subtotal + shipping
    
    if request.method == "POST":
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        address = request.POST.get('address', '')
        town_city = request.POST.get('town_city', '')
        country = request.POST.get('country', '')
        postcode_zip = request.POST.get('postcode_zip', '')
        mobile = request.POST.get('mobile', '')
        email = request.POST.get('email', '')
        order_notes = request.POST.get('order_notes', '')
        
        pm_value = request.POST.get('payment_method', 'Delivery')
        payment_method = 'Cash On Delivery'
        if pm_value == 'Transfer': payment_method = 'Direct Bank Transfer'
        elif pm_value == 'Payments': payment_method = 'Check Payments'
        elif pm_value == 'Paypal': payment_method = 'Paypal'
        elif pm_value == 'Delivery': payment_method = 'Cash On Delivery'
        
        if not all([first_name, last_name, address, town_city, country, postcode_zip, mobile, email]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('checkout')
            
        # Final stock check before processing order
        for item in cart_items:
            if item.product.stock_quantity < item.quantity:
                messages.error(request, f"Stock for {item.product.name} is insufficient (Only {item.product.stock_quantity} left). Please update your cart.")
                return redirect('cart')

        order = Order.objects.create(
            customer=customer,
            first_name=first_name,
            last_name=last_name,
            address=address,
            town_city=town_city,
            country=country,
            postcode_zip=postcode_zip,
            mobile=mobile,
            email=email,
            order_notes=order_notes,
            total_amount=total,
            payment_method=payment_method
        )
        
        for item in cart_items:
            # Deduct stock
            product = item.product
            product.stock_quantity -= item.quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price,
                quantity=item.quantity
            )
            
        cart_items.delete()
        messages.success(request, "Order placed successfully! Stock has been updated.")
        return redirect('home')
    
    context = {
        'categories': Category.objects.all(),
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
        'customer': customer,
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
