import re, random, time, secrets
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.db.models.functions import Lower
from datetime import timedelta
from django.utils import timezone
from django.core.paginator import Paginator
from .utils import get_paginated_data
from decimal import Decimal, InvalidOperation
import json
from .models import Customer, Category, Product, Cart, Order, OrderItem, Wishlist, Brand, ProductReview, Coupon, ProductVariant, Attribute, AttributeValue
from .services.currency_service import CurrencyService
from .services.coupon_service import apply_coupon, get_applied_coupon, clear_coupon
from django.db.models import F
from django.views.decorators.http import require_POST

from .logger import log_action

# Invoice PDF Generation Imports
from playwright.sync_api import sync_playwright
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import razorpay

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# =========================================================================
#  PAGE VIEWS  —  These render full HTML pages
# =========================================================================

def about(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'about.html', context)

def bestseller(request):
    all_products = Product.objects.all().select_related('brand', 'category_id').order_by('-id')
    page_obj = get_paginated_data(request, all_products)
    
    context = {
        'categories': Category.objects.all(),
        'products': page_obj,
        'all_products': all_products,
    }
    return render(request, 'bestseller.html', context)

def buy_again(request, oid):
    if 'email' not in request.session:
        return redirect('login')
        
    customer = Customer.objects.get(email=request.session['email'])
    old_order = get_object_or_404(Order, pk=oid, customer=customer)
    
    for item in old_order.items.all():
        # Add to cart
        stock = item.variant.stock_quantity if item.variant else item.product.total_stock
        if stock > 0:
            cart_item, created = Cart.objects.get_or_create(customer=customer, product=item.product, variant=item.variant)
            if not created:
                # If already in cart, check stock
                if stock > cart_item.quantity:
                    cart_item.quantity += 1
                    cart_item.save()
            else:
                cart_item.quantity = 1
                cart_item.save()
                
    messages.success(request, f"Items from Order #{oid} added to your cart.")
    return redirect('cart')

def cancel_order(request, oid):
    if 'email' not in request.session:
        return redirect('login')
        
    customer = Customer.objects.get(email=request.session['email'])
    order = get_object_or_404(Order, pk=oid, customer=customer)
    
    if order.status == 'Pending':
        order.status = 'Cancelled'
        # Revert stock
        for item in order.items.all():
            if item.variant:
                item.variant.stock_quantity += item.quantity
                item.variant.save()
        order.save()
        log_action(f"Customer: {customer.full_name} <{customer.email}>", "Cancelled Order", f"Order #{oid}")
        messages.success(request, f"Order #{oid} has been cancelled.")
    else:
        messages.error(request, "This order cannot be cancelled.")
        
    return redirect('order_detail', oid=oid)

def cart(request):
    if 'email' not in request.session:
        return redirect('login')
    
    customer = Customer.objects.get(email=request.session['email'])
    cart_items = Cart.objects.filter(customer=customer)
    
    subtotal = sum(item.total_price() for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)
    shipping = 100 * cart_count
    
    # Coupon logic
    applied_coupon = get_applied_coupon(request.session)
    discount = Decimal('0.00')
    if applied_coupon:
        is_valid, msg = applied_coupon.is_valid(subtotal, customer=customer)
        if is_valid:
            discount = applied_coupon.calculate_discount(subtotal)
        else:
            messages.warning(request, f"Coupon removed: {msg}")
            clear_coupon(request.session)
            applied_coupon = None
            
    total = Decimal(str(subtotal)) - discount + Decimal(str(shipping))
    
    context = {
        'categories': Category.objects.all(),
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'discount': discount,
        'applied_coupon': applied_coupon,
        'total': total,
        'cart_count': cart_count,
    }
    return render(request, 'cart.html', context)

def category_products(request, cid):
    context = {
        'categories': Category.objects.all(),
    }
    if cid == 0:
        products = Product.objects.all().select_related('brand', 'category_id')
    else:
        category = Category.objects.get(id=cid)
        products = Product.objects.filter(category_id=category).select_related('brand', 'category_id')
        context['selected_category'] = category
    
    # Pagination (12 per page)
    page_obj = get_paginated_data(request, products, per_page=12)
    
    context['products'] = page_obj
    context['all_products'] = Product.objects.all() # For carousel if needed
    
    return render(request, 'index.html', context)

def checkout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    # Check if the user is allowed to access checkout
    if not request.session.get('checkout_allowed'):
        messages.error(request, "Please proceed to checkout from your cart.")
        return redirect('cart')
    
    customer = Customer.objects.get(email=request.session['email'])
    cart_items = Cart.objects.filter(customer=customer)
    
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart')
        
    subtotal = sum(item.total_price() for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)
    shipping = 100 * cart_count
    
    # Coupon logic
    applied_coupon = get_applied_coupon(request.session)
    discount = Decimal('0.00')
    if applied_coupon:
        is_valid, _ = applied_coupon.is_valid(subtotal, customer=customer)
        if is_valid:
            discount = applied_coupon.calculate_discount(subtotal)
        else:
            clear_coupon(request.session)
            applied_coupon = None

    total = Decimal(str(subtotal)) - discount + Decimal(str(shipping))
    
    if request.method == "POST":
        order_notes = request.POST.get('order_notes', '')
        pm_value = request.POST.get('payment_method', 'Delivery')
        
        payment_method = 'Cash On Delivery'
        if pm_value == 'Transfer': payment_method = 'Direct Bank Transfer'
        elif pm_value == 'Payments': payment_method = 'Check Payments'
        elif pm_value == 'Paypal': payment_method = 'Paypal'
        elif pm_value == 'Delivery': payment_method = 'Cash On Delivery'
        
        # Ensure customer has an address before allowing order
        if not all([customer.full_name, customer.address, customer.town_city, customer.state, customer.country, customer.postcode_zip]):
            messages.error(request, "Please update your shipping address in your profile before placing an order.")
            return redirect('my_account')

        # Final stock check before processing order
        for item in cart_items:
            available_stock = item.variant.stock_quantity if item.variant else item.product.total_stock
            if available_stock < item.quantity:
                messages.error(request, f"Stock for {item.product.full_name} is insufficient (Only {available_stock} left). Please update your cart.")
                return redirect('cart')

        # Final Coupon Validation inside transaction
        with transaction.atomic():
            final_coupon = None
            final_discount = Decimal('0.00')
            if applied_coupon:
                # Refresh from DB with lock
                coupon_db = Coupon.objects.select_for_update().get(pk=applied_coupon.pk)
                is_valid, msg = coupon_db.is_valid(subtotal, customer=customer)
                if is_valid:
                    final_coupon = coupon_db
                    final_discount = coupon_db.calculate_discount(subtotal)
                    # Increment usage
                    Coupon.objects.filter(pk=coupon_db.pk).update(used_count=F('used_count') + 1)
                    if customer:
                        coupon_db.used_by_customers.add(customer)
                else:
                    messages.error(request, f"Coupon failed at final validation: {msg}")
                    clear_coupon(request.session)
                    return redirect('cart')

            order = Order.objects.create(
                customer=customer,
                order_notes=order_notes,
                total_amount=total, 
                payment_method=payment_method,
                shipping_charge=shipping,
                coupon=final_coupon,
                discount_amount=final_discount
            )
            
            log_action(f"Customer: {customer.full_name} <{customer.email}>", "Placed Order", f"Order #{order.id} | Total: {total}")
            
            for item in cart_items:
                # Determine the stock entity and price to use
                product = item.product
                if item.variant:
                    # Decrement variant stock
                    item.variant.stock_quantity -= item.quantity
                    item.variant.save()
                    snap_price = item.variant.effective_price
                    snap_sku   = item.variant.sku
                    snap_attrs = {
                        va.attribute_value.attribute.name: va.attribute_value.value
                        for va in item.variant.variantattribute_set.select_related(
                            'attribute_value__attribute'
                        ).all()
                    }
                else:
                    # product.stock_quantity -= item.quantity # No longer maintained
                    # product.save()
                    snap_price = product.min_price
                    snap_sku   = ''
                    snap_attrs = {}

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=item.variant,
                    price=int(snap_price),
                    quantity=item.quantity,
                    snapshot_sku=snap_sku,
                    snapshot_price=snap_price,
                    snapshot_attributes=snap_attrs,
                )

        # Trigger Order Confirmation Email (now that items are created)
        import threading
        from .email_utils import send_order_email
        threading.Thread(target=send_order_email, args=(order, 'confirmation')).start()
            
        cart_items.delete()
        clear_coupon(request.session)
        
        # Clear the checkout authorization flag
        if 'checkout_allowed' in request.session:
            del request.session['checkout_allowed']
            
        messages.success(request, "Order placed successfully! Stock has been updated.")
        return redirect('home')
    
    context = {
        'categories': Category.objects.all(),
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'discount': discount,
        'applied_coupon': applied_coupon,
        'total': total,
        'customer': customer,
        'cart_count': cart_count,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'checkout.html', context)

def compare_view(request):
    ids_str = request.GET.get('ids', '')
    product_ids = [id.strip() for id in ids_str.split(',') if id.strip().isdigit()]
    
    # Limit to 4 products as per requirements
    product_ids = product_ids[:4]
    
    products = Product.objects.filter(id__in=product_ids).select_related('brand', 'category_id')
    
    # Ensure order matches the input
    product_dict = {p.id: p for p in products}
    ordered_products = [product_dict[int(pid)] for pid in product_ids if int(pid) in product_dict]
    
    # Calculate lowest price among selected products
    lowest_price = min([p.min_price for p in ordered_products]) if ordered_products else None

    context = {
        'categories': Category.objects.all(),
        'products': ordered_products,
        'lowest_price': lowest_price,
    }
    return render(request, 'compare.html', context)

def contact(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        log_action(f"Guest/User: {name} <{email}>", "Contact Form Submission", f"Subject: {subject} | Message: {message[:50]}...")
        messages.success(request, "Your message has been sent. We will get back to you soon.")
        return redirect('contact')

    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'contact.html', context)

def download_invoice(request, oid):
    is_admin = '_site_admin_user_id' in request.session
    is_customer = 'email' in request.session

    if not is_admin and not is_customer:
        return redirect('login')
        
    if is_admin:
        order = get_object_or_404(Order, pk=oid)
    else:
        customer = Customer.objects.get(email=request.session['email'])
        order = get_object_or_404(Order, pk=oid, customer=customer)
    
    context = {
        'order': order,
        'items': order.items.all(),
    }
    
    html_string = render_to_string('invoice.html', context)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_string)
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
    
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
    
    return response

def error_404(request, exception=None):
    context = {
        'error_type': '404 Not Found',
        'error_message': 'The page you are looking for does not exist.',
        'status_code': 404,
        'debug': settings.DEBUG,
    }
    return render(request, 'error.html', context, status=404)

def error_500(request):
    context = {
        'error_type': '500 Server Error',
        'error_message': 'An unexpected error occurred on our server.',
        'status_code': 500,
        'debug': settings.DEBUG,
    }
    return render(request, 'error.html', context, status=500)

def error_403(request, exception=None):
    context = {
        'error_type': '403 Forbidden',
        'error_message': 'You do not have permission to access this resource.',
        'status_code': 403,
        'debug': settings.DEBUG,
    }
    return render(request, 'error.html', context, status=403)

def error_400(request, exception=None):
    context = {
        'error_type': '400 Bad Request',
        'error_message': 'Your browser sent a request that this server could not understand.',
        'status_code': 400,
        'debug': settings.DEBUG,
    }
    return render(request, 'error.html', context, status=400)

def faq(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'faq.html', context)

def forgot_password(request):    
    if request.method == "POST":
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.get_all_if_any()}) # Category logic dummy

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
            log_action(f"Guest ({get_client_ip(request)})", "Requested Password Reset", f"Email: {email}")
            return redirect('reset_password')
        except Exception as e:
            messages.error(request, "Failed to send OTP. Please check email configuration.")
            return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

    return render(request, 'forgot_password.html', {'categories': Category.objects.all()})

def help(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'help.html', context)

def home(request):
    from django.db.models import Sum
    all_products = Product.objects.all().select_related('brand', 'category_id').order_by('-id')
    featured_products_all = Product.objects.filter(is_featured=True).select_related('brand', 'category_id')
    new_arrivals = Product.objects.all().select_related('brand', 'category_id').order_by('-id')[:8]
    featured_tab = featured_products_all[:8]
    top_selling = Product.objects.annotate(total_sold=Sum('orderitem__quantity')).order_by('-total_sold')[:8]
    
    # Prioritize iPhone for special offer
    special_offer = Product.objects.filter(model_name__icontains='iPhone').order_by('?').first()
    if not special_offer:
        special_offer = featured_products_all.order_by('?').first()

    page_obj = get_paginated_data(request, all_products)
    
    context = {
        'categories': Category.objects.all(),
        'products': page_obj,
        'all_products': all_products,
        'featured_products': featured_products_all[:5], # For carousel
        'special_offer': special_offer,
        'new_arrivals': new_arrivals,
        'featured_tab': featured_tab,
        'top_selling': top_selling,
    }
    return render(request, 'index.html', context)

def index(request):
    from django.db.models import Sum
    all_products = Product.objects.all().select_related('brand', 'category_id').order_by('-id')
    featured_products_all = Product.objects.filter(is_featured=True).select_related('brand', 'category_id')
    new_arrivals = Product.objects.all().select_related('brand', 'category_id').order_by('-id')[:8]
    featured_tab = featured_products_all[:8]
    top_selling = Product.objects.annotate(total_sold=Sum('orderitem__quantity')).order_by('-total_sold')[:8]
    
    # Prioritize iPhone for special offer
    special_offer = Product.objects.filter(model_name__icontains='iPhone').order_by('?').first()
    if not special_offer:
        special_offer = featured_products_all.order_by('?').first()

    page_obj = get_paginated_data(request, all_products)
    
    context = {
        'categories': Category.objects.all(),
        'products': page_obj,
        'all_products': all_products,
        'featured_products': featured_products_all[:5], # For carousel
        'special_offer': special_offer,
        'new_arrivals': new_arrivals,
        'featured_tab': featured_tab,
        'top_selling': top_selling,
    }
    return render(request, 'index.html', context)

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
            log_action(f"Customer: {customer.full_name} <{customer.email}>", "Login", "Successfully logged in.")
            return redirect('home')
        else:
            log_action(f"Guest ({get_client_ip(request)})", "Failed Login Attempt", f"Email: {email}")
            messages.error(request, "Invalid email or password.")
            return render(request, 'login.html', {'categories': Category.objects.all()})

    return render(request, 'login.html', {'categories': Category.objects.all()})

def logout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    email = request.session.get('email')
    name = request.session.get('name', 'User')
    user_info = f"Customer: {name} <{email}>"
    
    request.session.flush()
    log_action(user_info, "Logout", "Logged out successfully.")
    messages.success(request, "You have been logged out.")
    return redirect('login')

def my_account(request):
    if 'email' not in request.session:
        return redirect('login')
    
    customer = Customer.objects.get(email=request.session['email'])
    active_tab = request.GET.get('tab', 'dashboard')
    
    context = {
        'categories': Category.objects.all(),
        'customer': customer,
        'active_tab': active_tab,
    }
    
    if active_tab == 'orders':
        orders = Order.objects.filter(customer=customer).prefetch_related('items__product').order_by('-created_at')
        
        # 1. Date range filter
        date_filter = request.GET.get('date_range')
        now = timezone.now()
        if date_filter == '30d':
            orders = orders.filter(created_at__gte=now - timedelta(days=30))
        elif date_filter == '3m':
            orders = orders.filter(created_at__gte=now - timedelta(days=90))
        elif date_filter == '6m':
            orders = orders.filter(created_at__gte=now - timedelta(days=180))
        elif date_filter == '1y':
            orders = orders.filter(created_at__gte=now - timedelta(days=365))
            
        # 2. Status filter
        status_filter = request.GET.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
            
        # 3. Search (Order # or Product Name)
        query = request.GET.get('q')
        if query:
            if query.isdigit():
                orders = orders.filter(id=int(query))
            else:
                orders = orders.filter(items__product__name__icontains=query).distinct()
                
        # 4. Pagination (10 per page)
        page_obj = get_paginated_data(request, orders, per_page=10)
        
        context.update({
            'orders': page_obj,
            'date_filter': date_filter,
            'status_filter': status_filter,
            'search_query': query,
        })
    
    elif active_tab == 'wishlist':
        wishlist_items = Wishlist.objects.filter(customer=customer).select_related('product')
        context['wishlist_items'] = wishlist_items
        
    elif active_tab == 'profile':
        if request.method == "POST":
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            town_city = request.POST.get('town_city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            postcode_zip = request.POST.get('postcode_zip')

            if email != customer.email and Customer.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
            else:
                customer.full_name = full_name
                customer.email = email
                customer.phone = phone
                customer.address = address
                customer.town_city = town_city
                customer.state = state
                customer.country = country
                customer.postcode_zip = postcode_zip
                customer.save()
                
                request.session['email'] = email
                request.session['name'] = full_name
                messages.success(request, "Profile updated successfully.")
                log_action(f"Customer: {customer.full_name} <{customer.email}>", "Changed Account Details", f"Updated Profile Fields")
                return redirect('my_account')
    
    elif active_tab == 'dashboard':
        context['recent_orders'] = Order.objects.filter(customer=customer).order_by('-created_at')[:3]
        context['wishlist_count'] = Wishlist.objects.filter(customer=customer).count()
        context['total_orders'] = Order.objects.filter(customer=customer).count()

    return render(request, 'my_account.html', context)

def order_detail(request, oid):
    if 'email' not in request.session:
        return redirect('login')
    
    customer = Customer.objects.get(email=request.session['email'])
    order = get_object_or_404(Order, pk=oid, customer=customer)
    
    # Mask payment method for display if it's more than just COD
    masked_payment = order.payment_method
    if "Visa" in order.payment_method or "Master" in order.payment_method:
        # Example: Visa ****4242 (assuming it's stored that way, but if it's just a string, we might just show it)
        pass 
        
    context = {
        'categories': Category.objects.all(),
        'order': order,
        'items': order.items.all(),
        'masked_payment': masked_payment,
    }
    return render(request, 'order_detail.html', context)

def order_history(request):
    return redirect('/my-account/?tab=orders')

def privacy_policy(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'privacy_policy.html', context)

def proceed_to_checkout(request):
    if 'email' not in request.session:
        return redirect('login')
    
    # Set the session flag to allow access to checkout
    request.session['checkout_allowed'] = True
    return redirect('checkout')

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

        customer = Customer.objects.create(full_name=name, email=email, password=password)
        log_action(f"Guest ({get_client_ip(request)})", "Registered Account", f"Customer: {name} <{email}>")
        
        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')

    return render(request, 'register.html', {'categories': Category.objects.all()})

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

def return_order(request, oid):
    if 'email' not in request.session:
        return redirect('login')
        
    customer = Customer.objects.get(email=request.session['email'])
    order = get_object_or_404(Order, pk=oid, customer=customer)
    
    if order.status == 'Delivered':
        order.status = 'Returned'
        order.save()
        messages.success(request, f"Return initiated for Order #{oid}.")
    else:
        messages.error(request, "This order is not eligible for return.")
        
    return redirect('order_detail', oid=oid)

def returns(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'returns.html', context)

def warranty(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'warranty.html', context)

def shop(request, cid=0):
    from django.db.models import Q, Count
    
    # Get initial queryset
    products = Product.objects.all().select_related('brand', 'category_id')

    # 1. Build context with filters
    context = {
        'categories': Category.objects.all(),
        'brands': Brand.objects.annotate(product_count=Count('products')).filter(product_count__gt=0),
    }
    
    # 2. Category filtering
    get_cid = request.GET.get('cid')
    if get_cid:
        try: cid = int(get_cid)
        except ValueError: pass

    if cid != 0:
        try:
            category = Category.objects.get(id=cid)
            products = products.filter(category_id=category)
            context['selected_category'] = category
        except Category.DoesNotExist:
            pass

    # 3. Brand filtering
    brand_id = request.GET.get('brand')
    if brand_id:
        try:
            products = products.filter(brand_id=brand_id)
            context['selected_brand_id'] = int(brand_id)
        except ValueError:
            pass

    # 4. Search query
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(model_name__icontains=query) | 
            Q(brand__name__icontains=query) |
            Q(variant_specs__icontains=query) |
            Q(name__icontains=query) # Fallback for unmigrated
        )
        context['search_query'] = query

    # 5. Price filter
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            products = products.filter(variants__price__lte=float(max_price)).distinct()
            context['current_max_price'] = max_price
        except ValueError:
            pass

    # 6. Sorting
    sort = request.GET.get('sort', 'Name, A-Z')
    # Use annotated names for case-insensitive sort if available
    # For now, let's keep it simple: Sort by brand name, then model name
    sort_map = {
        'Name, A-Z':   ('brand__name', 'model_name'),
        'Name, Z-A':   ('-brand__name', '-model_name'),
        'Price, ASC':  ('variants__price',),
        'Price, DESC': ('-variants__price',),
    }
    order_fields = sort_map.get(sort, ('brand__name', 'model_name'))
    products = products.order_by(*order_fields)
    
    context['current_sort'] = sort
    
    # 7. Pagination (12 per page)
    page_obj = get_paginated_data(request, products, per_page=12)
    
    context['products'] = page_obj
    return render(request, 'shop.html', context)

def single(request, pid):
    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'variants__attributes'),
        pk=pid
    )
    
    # Track view
    from .models import ProductView
    ProductView.objects.create(product=product)

    related_products = Product.objects.filter(
        category_id=product.category_id
    ).exclude(pk=pid)[:3]
    customer = None
    user_has_reviewed = False
    
    # Build variant data for the frontend
    variants = product.variants.filter(is_active=True).prefetch_related(
        'variantattribute_set__attribute_value__attribute'
    )

    # Group attributes by their type for the variant selector UI
    attribute_groups = {}  # {attr_name: [{id, value, hex_color, display_order}, ...]}
    for variant in variants:
        for va in variant.variantattribute_set.all():
            av = va.attribute_value
            attr_name = av.attribute.name
            if attr_name not in attribute_groups:
                attribute_groups[attr_name] = []
            entry = {
                'id': av.id,
                'value': av.value,
                'hex_color': av.hex_color,
                'display_order': av.display_order,
            }
            if entry not in attribute_groups[attr_name]:
                attribute_groups[attr_name].append(entry)

    # Sort each group by display_order
    for attr_name in attribute_groups:
        attribute_groups[attr_name] = sorted(
            attribute_groups[attr_name], key=lambda x: x['display_order']
        )

    has_variants = variants.exists()
    
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()
        if customer:
            user_has_reviewed = ProductReview.objects.filter(product=product, customer=customer).exists()

    if not customer:
        ip = get_client_ip(request)
        user_has_reviewed = ProductReview.objects.filter(product=product, ip_address=ip).exists()
        
        if not user_has_reviewed and request.session.session_key:
            user_has_reviewed = ProductReview.objects.filter(product=product, session_key=request.session.session_key).exists()

    context = {
        'categories': Category.objects.all(),
        'product': product,
        'related_products': related_products,
        'customer': customer,
        'user_has_reviewed': user_has_reviewed,
        'has_variants': has_variants,
        'attribute_groups': attribute_groups,
        'base_gallery_json': json.dumps([
            {'url': product.featured_image_url, 'alt': product.full_name}
        ] if product.featured_image_url else []),
        'variants_json': json.dumps([
            {
                'id': v.id,
                'sku': v.sku,
                'price': str(v.effective_price),
                'stock_quantity': v.stock_quantity,
                'in_stock': v.in_stock,
                'attributes': {
                    va.attribute_value.attribute.name: va.attribute_value.value
                    for va in v.variantattribute_set.all()
                },
                'attribute_ids': [
                    va.attribute_value.id for va in v.variantattribute_set.all()
                ],
                'featured_image': v.primary_image.image_url if v.primary_image else product.featured_image_url,
            }
            for v in variants
        ])
    }
    return render(request, 'single.html', context)

def sitemap(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'sitemap.html', context)

def support(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'support.html', context)

def terms(request):
    context = {
        'categories': Category.objects.all(),
    }
    return render(request, 'terms.html', context)

def wishlist(request):
    return redirect('/my-account/?tab=wishlist')

# =========================================================================
#  AJAX VIEWS  —  These return JSON responses
# =========================================================================

def add_to_cart(request, pid):
    if 'email' not in request.session:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Please login first.'})
        messages.error(request, "Please login first.")
        return redirect('login')
    
    product = get_object_or_404(Product, pk=pid)
    customer = Customer.objects.get(email=request.session['email'])
    
    qty = request.POST.get('qty') or request.GET.get('qty', 1)
    try:
        qty = int(qty)
    except ValueError:
        qty = 1

    # --- Variant support ---
    variant = None
    variant_id = request.POST.get('variant_id') or request.GET.get('variant_id')
    if variant_id:
        try:
            variant = ProductVariant.objects.select_related('product').get(
                pk=int(variant_id), product=product, is_active=True
            )
        except (ProductVariant.DoesNotExist, ValueError):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Selected variant not found.'})
            messages.error(request, "Selected variant not found.")
            return redirect(request.META.get('HTTP_REFERER', 'cart'))

    # Stock check against the appropriate entity
    if variant:
        available_stock = variant.stock_quantity
        stock_label = variant.sku
    else:
        available_stock = product.total_stock
        stock_label = product.full_name

    cart_filter = {'customer': customer, 'product': product, 'variant': variant}
    cart_item = Cart.objects.filter(**cart_filter).first()
    current_qty = cart_item.quantity if cart_item else 0
    
    if available_stock < current_qty + qty:
        err_msg = f"Only {available_stock} units of {stock_label} are available. You already have {current_qty} in cart."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': err_msg})
        messages.error(request, err_msg)
        return redirect(request.META.get('HTTP_REFERER', 'cart'))

    if cart_item:
        cart_item.quantity += qty
        cart_item.save()
    else:
        cart_item = Cart.objects.create(
            customer=customer, product=product, variant=variant, quantity=qty
        )
        
    cart_items = Cart.objects.filter(customer=customer)
    cart_count = sum(item.quantity for item in cart_items)
    cart_total = sum(item.total_price() for item in cart_items)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"{product.full_name} added to cart.",
            'cart_count': cart_count,
            'cart_total': cart_total
        })

    messages.success(request, f"{product.full_name} added to cart.")
    return redirect(request.META.get('HTTP_REFERER', 'cart'))

def toggle_wishlist(request, pid):
    if 'email' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'Please login first.'})

    customer = Customer.objects.get(email=request.session['email'])
    product = get_object_or_404(Product, pk=pid)

    wishlist_item = Wishlist.objects.filter(customer=customer, product=product).first()

    if wishlist_item:
        wishlist_item.delete()
        return JsonResponse({'status': 'success', 'action': 'removed', 'message': f'{product.full_name} removed from wishlist.'})
    else:
        Wishlist.objects.create(customer=customer, product=product)
        return JsonResponse({'status': 'success', 'action': 'added', 'message': f'{product.full_name} added to wishlist.'})

def update_cart(request, cid, action):
    if 'email' not in request.session:
        return redirect('login')
        
    customer = Customer.objects.get(email=request.session['email'])
    cart_item = get_object_or_404(Cart, pk=cid, customer=customer)
    
    if action == 'increase':
        available_stock = cart_item.variant.stock_quantity if cart_item.variant else cart_item.product.total_stock
        if available_stock > cart_item.quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': f"Only {available_stock} units available."})
            messages.error(request, f"Only {available_stock} units available for {cart_item.product.full_name}.")
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
    cart_count = sum(item.quantity for item in cart_items)
    shipping = 100 * cart_count
    
    # Coupon support for update-cart
    applied_coupon = get_applied_coupon(request.session)
    discount = Decimal('0.00')
    if applied_coupon:
        is_valid, _ = applied_coupon.is_valid(subtotal, customer=customer)
        if is_valid:
            discount = applied_coupon.calculate_discount(subtotal)
        else:
            clear_coupon(request.session)
            applied_coupon = None

    total = Decimal(str(subtotal)) - discount + Decimal(str(shipping))

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
            'subtotal': str(subtotal),
            'shipping': str(shipping),
            'discount': str(discount),
            'total': str(total),
            'cart_count': cart_count,
            'removed': action == 'remove' or not Cart.objects.filter(id=cid).exists(),
            'coupon_applied': applied_coupon is not None
        })

    return redirect('cart')

# =========================================================================
#  VARIANT OPTIONS API
# =========================================================================

def variant_options_api(request):
    """
    GET /api/variant-options/?product_id=42&color=3&storage=7
    Returns all active variants for a product, optionally filtered by
    attribute_value IDs. Returns a 'selected_variant' only when the
    provided IDs resolve to exactly one active variant.
    """
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'product_id required'}, status=400)

    product = get_object_or_404(Product, pk=product_id)
    all_variants = product.variants.filter(is_active=True).prefetch_related(
        'variantattribute_set__attribute_value__attribute',
    )

    # Collect any attribute_value IDs supplied as query params
    # Query string may look like ?product_id=42&Color=3&Storage=7
    # or ?product_id=42&av_ids=3,7
    av_ids = []
    av_ids_param = request.GET.get('av_ids', '')
    if av_ids_param:
        av_ids = [int(x) for x in av_ids_param.split(',') if x.isdigit()]
    else:
        # Try to parse individual attribute params like ?Color=3
        for key, val in request.GET.items():
            if key not in ('product_id',) and val.isdigit():
                av_ids.append(int(val))

    def build_gallery(variant):
        # Uses the new color-scoped gallery property from the model
        return [
            {
                'url': request.build_absolute_uri(img.image.url), 
                'alt': img.alt_text or product.full_name
            } 
            for img in variant.gallery
        ]

    def serialize_variant(v):
        return {
            'id': v.id,
            'sku': v.sku,
            'price': str(v.effective_price),
            'stock_quantity': v.stock_quantity,
            'in_stock': v.in_stock,
            'attributes': {
                va.attribute_value.attribute.name: va.attribute_value.value
                for va in v.variantattribute_set.all()
            },
            'attribute_ids': [
                va.attribute_value.id for va in v.variantattribute_set.all()
            ],
            'gallery': build_gallery(v),
        }

    # Filter: include only variants that contain ALL requested av_ids
    if av_ids:
        matching = [
            v for v in all_variants
            if all(aid in [va.attribute_value.id for va in v.variantattribute_set.all()]
                   for aid in av_ids)
        ]
    else:
        matching = list(all_variants)

    selected_variant = None
    featured_gallery = None
    if matching:
        featured_gallery = build_gallery(matching[0])
        if len(matching) == 1:
            selected_variant = serialize_variant(matching[0])

    return JsonResponse({
        'available_variants': [serialize_variant(v) for v in matching],
        'selected_variant': selected_variant,
        'featured_gallery': featured_gallery,
    })


# =========================================================================
#  RATING SYSTEM API
# =========================================================================

def get_client_ip(request):
    """Helper to extract client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_product_rating(request, pid):
    """Fetch average rating and total votes for a specific product."""
    product = get_object_or_404(Product, pk=pid)
    ip = get_client_ip(request)
    session_key = request.session.session_key or ""
    
    already_voted = False
    customer = None
    
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()
        if customer:
            # Authenticated users are identified by their account
            already_voted = ProductReview.objects.filter(product=product, customer=customer).exists()
    
    if not customer:
        # Guests are identified by IP or Session
        if ProductReview.objects.filter(product=product, ip_address=ip).exists():
            already_voted = True
        elif session_key and ProductReview.objects.filter(product=product, session_key=session_key).exists():
            already_voted = True
    
    return JsonResponse({
        'product_id': product.id,
        'average': product.rating,
        'total_votes': product.total_votes,
        'already_voted': already_voted
    })

def submit_product_rating(request, pid):
    """
    Accepts a comprehensive product review.
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    product = get_object_or_404(Product, pk=pid)
    ip = get_client_ip(request)
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Identification
    customer = None
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()

    # Improved Duplicate Detection Logic
    if customer:
        if ProductReview.objects.filter(product=product, customer=customer).exists():
            return JsonResponse({'status': 'error', 'message': 'You have already reviewed this product.'}, status=403)
    else:
        # Only guest checks if not logged in
        if ProductReview.objects.filter(product=product, ip_address=ip).exists():
            return JsonResponse({'status': 'error', 'message': 'A guest review from your IP address has already been submitted.'}, status=403)
        if ProductReview.objects.filter(product=product, session_key=session_key).exists():
            return JsonResponse({'status': 'error', 'message': 'You have already reviewed this product in this session.'}, status=403)

    try:
        data = json.loads(request.body)
        rating_value = int(data.get('rating', 0))
        review_text = data.get('review_text', '').strip()
        name = data.get('name', 'Anonymous').strip()
        email = data.get('email', '').strip()
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid data format.'}, status=400)
    
    # Validation
    if not rating_value or rating_value < 1 or rating_value > 5:
        return JsonResponse({'status': 'error', 'message': 'Please provide a star rating (1-5).'}, status=400)
    
    if not review_text:
        return JsonResponse({'status': 'error', 'message': 'Review comment is mandatory.'}, status=400)

    # Use session data if missing and logged in
    if customer:
        name = customer.full_name
        email = customer.email

    with transaction.atomic():
        ProductReview.objects.create(
            product=product,
            customer=customer,
            name=name,
            email=email,
            rating=rating_value,
            review_text=review_text,
            ip_address=ip,
            session_key=session_key
        )
        
    user_info = f"Customer: {customer.full_name} <{customer.email}>" if customer else f"Guest ({ip})"
    log_action(user_info, "Left a Review", f"Product: {product.full_name} | Rating: {rating_value}")

    return JsonResponse({
        'status': 'success',
        'average': product.rating,
        'total_votes': product.total_votes,
        'message': f'Thank you! Your review for "{product.full_name}" has been submitted.'
    })

# =========================================================================
#  RAZORPAY INTEGRATION
# =========================================================================

@csrf_exempt
def create_razorpay_order(request):
    """
    Creates a Razorpay Order ID and returns it to the frontend.
    """
    if 'email' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'Please login first.'}, status=403)
    
    customer = Customer.objects.get(email=request.session['email'])
    cart_items = Cart.objects.filter(customer=customer)
    
    if not cart_items.exists():
        return JsonResponse({'status': 'error', 'message': 'Your cart is empty.'}, status=400)
    
    subtotal = sum(item.total_price() for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)
    shipping = 100 * cart_count
    # Coupon logic for Razorpay
    applied_coupon = get_applied_coupon(request.session)
    discount = Decimal('0.00')
    if applied_coupon:
        is_valid, _ = applied_coupon.is_valid(subtotal, customer=customer)
        if is_valid:
            discount = applied_coupon.calculate_discount(subtotal)
            
    total = Decimal(str(subtotal)) - discount + Decimal(str(shipping))
    
    try:
        # Create Razorpay Order
        # amount is in paise (1 INR = 100 paise)
        data = {
            "amount": int(total * 100),
            "currency": "INR",
            "receipt": f"receipt_{secrets.token_hex(4)}",
            "notes": {
                "customer_email": customer.email,
                "cart_item_count": cart_count
            }
        }
        razorpay_order = client.order.create(data=data)
        
        return JsonResponse({
            'order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'key_id': settings.RAZORPAY_KEY_ID,
            'customer_name': customer.full_name,
            'customer_email': customer.email,
            'customer_phone': customer.phone or ""
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@csrf_exempt
def verify_razorpay_payment(request):
    """
    Verifies the Razorpay payment signature and finalizes the order.
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
        
    try:
        data = json.loads(request.body)
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        order_notes = data.get('order_notes', '')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        
    # Verify signature
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'status': 'error', 'message': 'Signature verification failed'}, status=400)

    # Signature valid, create the order
    if 'email' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'Session expired'}, status=403)
        
    customer = Customer.objects.get(email=request.session['email'])
    cart_items = Cart.objects.filter(customer=customer)
    
    if not cart_items.exists():
        return JsonResponse({'status': 'error', 'message': 'Cart empty'}, status=400)
        
    try:
        with transaction.atomic():
            subtotal = sum(item.total_price() for item in cart_items)
            subtotal = sum(item.total_price() for item in cart_items)
            cart_count = sum(item.quantity for item in cart_items)
            shipping = 100 * cart_count

            # Coupon logic
            applied_coupon = get_applied_coupon(request.session)
            final_coupon = None
            final_discount = Decimal('0.00')
            if applied_coupon:
                # We already have a transaction context from above (atomic)
                coupon_db = Coupon.objects.select_for_update().get(pk=applied_coupon.pk)
                is_valid, msg = coupon_db.is_valid(subtotal, customer=customer)
                if is_valid:
                    final_coupon = coupon_db
                    final_discount = coupon_db.calculate_discount(subtotal)
                    # Increment usage
                    Coupon.objects.filter(pk=coupon_db.pk).update(used_count=F('used_count') + 1)
                    if customer:
                        coupon_db.used_by_customers.add(customer)
                # If not valid, we proceed without discount (already reflected in Razorpay amount)
                # but it shouldn't happen usually as we check before creating RZ order.

            total = Decimal(str(subtotal)) - final_discount + Decimal(str(shipping))
            
            order = Order.objects.create(
                customer=customer,
                order_notes=order_notes,
                total_amount=total,
                payment_method='Razorpay Online',
                shipping_charge=shipping,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
                payment_status='Succeeded',
                status='Processing',
                coupon=final_coupon,
                discount_amount=final_discount
            )
            
            for item in cart_items:
                product = item.product
                if item.variant:
                    item.variant.stock_quantity -= item.quantity
                    item.variant.save()
                    snap_price = item.variant.effective_price
                    snap_sku   = item.variant.sku
                    snap_attrs = {
                        va.attribute_value.attribute.name: va.attribute_value.value
                        for va in item.variant.variantattribute_set.select_related(
                            'attribute_value__attribute'
                        ).all()
                    }
                else:
                    # product.stock_quantity -= item.quantity
                    # product.save()
                    snap_price = product.min_price
                    snap_sku   = ''
                    snap_attrs = {}

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=item.variant,
                    price=int(snap_price),
                    quantity=item.quantity,
                    snapshot_sku=snap_sku,
                    snapshot_price=snap_price,
                    snapshot_attributes=snap_attrs,
                )
                
            log_action(f"Customer: {customer.full_name}", "Placed Order (Razorpay)", f"Order #{order.id} | PayID: {razorpay_payment_id}")
            
            # Send confirmation email
            from .email_utils import send_order_email
            import threading
            threading.Thread(target=send_order_email, args=(order, 'confirmation')).start()
            
            # Clear cart
            cart_items.delete()
            clear_coupon(request.session)
            
            # Clear session checkout flag
            if 'checkout_allowed' in request.session:
                del request.session['checkout_allowed']
                
            return JsonResponse({'status': 'success', 'order_id': order.id})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def payment_success(request):
    """
    Success page after checkout.
    """
    order_id = request.GET.get('order_id')
    return render(request, 'payment_success.html', {'order_id': order_id})

def exchange_rates(request):
    """
    API endpoint that returns the latest exchange rates.
    Implements L1 caching (Server-side) and logs hits/misses.
    """
    rates_data = CurrencyService.get_rates()
    return JsonResponse(rates_data)

@require_POST
def apply_coupon_view(request):
    try:
        data = json.loads(request.body)
        code = data.get('code')
    except:
        return JsonResponse({"success": False, "message": "Invalid request."})

    customer = None
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()

    if 'coupon_id' in request.session:
        return JsonResponse({"success": False, "message": "Only one coupon can be applied per order."})

    # Calculate current cart total (before shipping)
    cart_items = Cart.objects.filter(customer=customer)
    subtotal = sum(item.total_price() for item in cart_items)

    result = apply_coupon(code, Decimal(str(subtotal)), request.session, customer=customer)
    
    # Format decimals for JSON
    result['discount'] = str(result['discount'])
    # Add shipping back to the new_total so the frontend 'Grand Total' is correct
    cart_count = sum(item.quantity for item in cart_items)
    shipping = Decimal('100.00') * cart_count
    result['new_total'] = str(Decimal(result['new_total']) + shipping)
    result['subtotal'] = str(subtotal)
    result['shipping'] = str(shipping)
    
    result['total'] = result['new_total'] # Consistency with update_cart
    
    return JsonResponse(result)

@require_POST
def remove_coupon_view(request):
    clear_coupon(request.session)
    return JsonResponse({"success": True, "message": "Coupon removed."})
