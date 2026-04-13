from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from functools import wraps
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .models import (
    Customer, Category, Product, Cart, Order, OrderItem, 
    SiteAdmin, Brand, Coupon, ProductVariant
)
from .forms import CategoryForm, ProductForm, BrandForm, ProductImageFormSet, CouponForm
from .logger import log_action
from .exports import export_to_csv, export_to_excel, export_to_word, export_to_pdf
from datetime import datetime
from .services.currency_service import CurrencyService

# ─────────────────────────────────────────────────────────────────────────────
# Authentication Decorator
# ─────────────────────────────────────────────────────────────────────────────
def site_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # We check for a specific site admin session key to avoid session sharing with django-admin
        admin_id = request.session.get('_site_admin_user_id')
        if not admin_id:
            login_url = reverse('custom_admin:login')
            return redirect(f'{login_url}?next={request.path}')
        
        # Verify the user still exists and has the profile
        try:
            admin_user = User.objects.get(pk=admin_id)
            if not hasattr(admin_user, 'site_admin_profile'):
                raise User.DoesNotExist
            # Attach to request for easy access in templates
            request.site_admin = admin_user
        except User.DoesNotExist:
            if '_site_admin_user_id' in request.session:
                del request.session['_site_admin_user_id']
            messages.error(request, "Invalid session. Please login again.")
            return redirect(reverse('custom_admin:login'))
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ─────────────────────────────────────────────────────────────────────────────
# ALPHABETICAL ADMIN VIEWS
# ─────────────────────────────────────────────────────────────────────────────
@site_admin_required
def admin_brands(request):
    brand_list = Brand.objects.order_by('id')
    paginator = Paginator(brand_list, 10)
    page_number = request.GET.get('page')
    brands = paginator.get_page(page_number)
    
    context = {'active_page': 'brands', 'brands': brands}
    return render(request, 'custom_admin/brands.html', context)

@site_admin_required
def admin_brand_add(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            brand = form.save()
            log_action(f"Admin: {request.site_admin.username}", "Created Brand", f"Brand: {brand.name}")
            messages.success(request, "Brand created successfully.")
            return redirect('custom_admin:brands')
    else:
        form = BrandForm()
    
    context = {'active_page': 'brands', 'form': form, 'title': 'Add Brand'}
    return render(request, 'custom_admin/brand_form.html', context)

@site_admin_required
def admin_brand_delete(request, brand_id):
    brand = get_object_or_404(Brand, pk=brand_id)
    product_count = brand.products.count()
    
    if request.method == 'POST':
        name = brand.name
        brand.delete()
        log_action(f"Admin: {request.site_admin.username}", "Deleted Brand", f"Brand: {name}")
        messages.success(request, f"Brand '{name}' deleted.")
        return redirect('custom_admin:brands')
    
    context = {
        'active_page': 'brands', 
        'item': brand, 
        'type': 'brand',
        'product_count': product_count
    }
    return render(request, 'custom_admin/delete_confirm.html', context)

@site_admin_required
def admin_brand_edit(request, brand_id):
    brand = get_object_or_404(Brand, pk=brand_id)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            log_action(f"Admin: {request.site_admin.username}", "Updated Brand", f"Brand: {brand.name}")
            messages.success(request, "Brand updated successfully.")
            return redirect('custom_admin:brands')
    else:
        form = BrandForm(instance=brand)
    
    context = {'active_page': 'brands', 'form': form, 'brand': brand, 'title': 'Edit Brand'}
    return render(request, 'custom_admin/brand_form.html', context)

@site_admin_required
def admin_categories(request):
    category_list = Category.objects.order_by('id')
    paginator = Paginator(category_list, 10)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    context = {'active_page': 'categories', 'categories': categories}
    return render(request, 'custom_admin/categories.html', context)

@site_admin_required
def admin_category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            log_action(f"Admin: {request.site_admin.username}", "Created Category", f"Category: {category.name}")
            messages.success(request, "Category created successfully.")
            return redirect('custom_admin:categories')
    else:
        form = CategoryForm()
    
    context = {'active_page': 'categories', 'form': form, 'title': 'Add Category'}
    return render(request, 'custom_admin/category_form.html', context)

@site_admin_required
def admin_category_delete(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    product_count = category.product_set.count() # Related name default
    
    if request.method == 'POST':
        name = category.name
        category.delete()
        log_action(f"Admin: {request.site_admin.username}", "Deleted Category", f"Category: {name}")
        messages.success(request, f"Category '{name}' deleted.")
        return redirect('custom_admin:categories')
    
    context = {
        'active_page': 'categories', 
        'item': category, 
        'type': 'category',
        'product_count': product_count
    }
    return render(request, 'custom_admin/delete_confirm.html', context)

@site_admin_required
def admin_category_edit(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            log_action(f"Admin: {request.site_admin.username}", "Updated Category", f"Category: {category.name}")
            messages.success(request, "Category updated successfully.")
            return redirect('custom_admin:categories')
    else:
        form = CategoryForm(instance=category)
    
    context = {'active_page': 'categories', 'form': form, 'category': category, 'title': 'Edit Category'}
    return render(request, 'custom_admin/category_form.html', context)

@site_admin_required
def admin_customers(request):
    query = request.GET.get('q')
    customers = Customer.objects.all().order_by('-created_at')
    
    if query:
        customers = customers.filter(Q(full_name__icontains=query) | Q(email__icontains=query))
        
    context = {'active_page': 'customers', 'customers': customers}
    return render(request, 'custom_admin/customers.html', context)

@site_admin_required
def admin_coupons(request):
    coupon_list = Coupon.objects.all().order_by('-valid_from')
    paginator = Paginator(coupon_list, 10)
    page_number = request.GET.get('page')
    coupons = paginator.get_page(page_number)
    
    from django.utils import timezone
    context = {'active_page': 'coupons', 'coupons': coupons, 'now': timezone.now()}
    return render(request, 'custom_admin/coupons.html', context)

@site_admin_required
def admin_coupon_add(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
            log_action(f"Admin: {request.site_admin.username}", "Created Coupon", f"Code: {coupon.code}")
            messages.success(request, "Coupon created successfully.")
            return redirect('custom_admin:coupons')
    else:
        form = CouponForm()
    
    context = {'active_page': 'coupons', 'form': form, 'title': 'Add Coupon'}
    return render(request, 'custom_admin/coupon_form.html', context)

@site_admin_required
def admin_coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            log_action(f"Admin: {request.site_admin.username}", "Updated Coupon", f"Code: {coupon.code}")
            messages.success(request, "Coupon updated successfully.")
            return redirect('custom_admin:coupons')
    else:
        form = CouponForm(instance=coupon)
    
    context = {'active_page': 'coupons', 'form': form, 'coupon': coupon, 'title': 'Edit Coupon'}
    return render(request, 'custom_admin/coupon_form.html', context)

@site_admin_required
def admin_coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == 'POST':
        code = coupon.code
        coupon.delete()
        log_action(f"Admin: {request.site_admin.username}", "Deleted Coupon", f"Code: {code}")
        messages.success(request, f"Coupon '{code}' deleted.")
        return redirect('custom_admin:coupons')
    
    context = {'active_page': 'coupons', 'item': coupon, 'type': 'coupon'}
    return render(request, 'custom_admin/delete_confirm.html', context)

@site_admin_required
def admin_export(request):
    module = request.GET.get('module')
    export_format = request.GET.get('format', 'csv')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    query = request.GET.get('q')
    
    # Base queryset based on module
    if module == 'customers':
        queryset = Customer.objects.all().order_by('-created_at')
        filename = f"customers_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Customer List"
        headers = ['ID', 'Name', 'Email', 'Phone', 'Joined', 'Status', 'Address', 'City', 'Country', 'ZIP']
        def data_func(obj):
            return [obj.id, obj.full_name, obj.email, obj.phone or 'N/A', obj.created_at.strftime('%Y-%m-%d %H:%M'), obj.status, obj.address or 'N/A', obj.town_city or 'N/A', obj.country or 'N/A', obj.postcode_zip or 'N/A']
            
    elif module == 'orders':
        queryset = Order.objects.select_related('customer').all().order_by('-created_at')
        filename = f"orders_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Orders List"
        headers = ['Order ID', 'Customer', 'Date', 'Total', 'Payment', 'Status']
        def data_func(obj):
            return [obj.id, obj.customer.full_name, obj.created_at.strftime('%Y-%m-%d %H:%M'), f"${obj.total_amount}", obj.payment_method, obj.status]

    elif module == 'order_details':
        queryset = OrderItem.objects.select_related('order', 'variant__product').all().order_by('-order__created_at')
        filename = f"order_details_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Order Details (Line Items)"
        headers = ['Order ID', 'Product', 'Variant SKU', 'Quantity', 'Unit Price', 'Subtotal']
        def data_func(obj):
            sku = obj.variant.sku if obj.variant else (obj.snapshot_sku or 'N/A')
            return [obj.order.id, obj.snapshot_product_name, sku, obj.quantity, f"₹{obj.snapshot_price}", f"₹{obj.line_total()}"]

    elif module == 'products':
        queryset = Product.objects.select_related('category_id', 'brand').all().order_by('brand__name', 'model_name')
        filename = f"products_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Product Listing"
        headers = ['ID', 'Brand', 'Model', 'Category', 'Starting Price', 'Total Stock', 'Status']
        def data_func(obj):
            stock = obj.total_stock
            status = 'In Stock' if stock > 0 else 'Out of Stock'
            return [obj.id, obj.brand.name if obj.brand else 'N/A', obj.model_name or 'N/A', obj.category_id.name, f"₹{obj.min_price}", stock, status]
            
    elif module == 'coupons':
        queryset = Coupon.objects.all().order_by('-valid_from')
        filename = f"coupons_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Coupons List"
        headers = ['Code', 'Type', 'Value', 'Min Purchase', 'Expiry', 'Status', 'Used']
        def data_func(obj):
            return [obj.code, obj.discount_type, f"{obj.value}", f"₹{obj.min_purchase_amount}", obj.valid_to.strftime('%Y-%m-%d'), 'Active' if obj.active else 'Inactive', f"{obj.used_count}/{obj.usage_limit or '∞'}"]
            
    else:
        messages.error(request, "Invalid export module.")
        return redirect('custom_admin:dashboard')

    # Apply date range filtering if applicable
    if start_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            if module == 'customers': queryset = queryset.filter(created_at__date__gte=sd)
            elif module == 'orders': queryset = queryset.filter(created_at__date__gte=sd)
            elif module == 'order_details': queryset = queryset.filter(order__created_at__date__gte=sd)
        except ValueError:
            pass
            
    if end_date:
        try:
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            if module == 'customers': queryset = queryset.filter(created_at__date__lte=ed)
            elif module == 'orders': queryset = queryset.filter(created_at__date__lte=ed)
            elif module == 'order_details': queryset = queryset.filter(order__created_at__date__lte=ed)
        except ValueError:
            pass

    # Apply search query filtering
    if query:
        if module == 'customers':
            queryset = queryset.filter(Q(full_name__icontains=query) | Q(email__icontains=query))
        elif module == 'orders':
            queryset = queryset.filter(Q(customer__full_name__icontains=query) | Q(id__icontains=query))
        elif module == 'products':
            queryset = queryset.filter(Q(brand__name__icontains=query) | Q(model_name__icontains=query) | Q(variants__sku__icontains=query)).distinct()

    # Export based on format
    if export_format == 'csv':
        return export_to_csv(queryset, filename, headers, data_func)
    elif export_format == 'excel':
        return export_to_excel(queryset, filename, headers, data_func)
    elif export_format == 'word':
        return export_to_word(queryset, filename, title, headers, data_func)
    elif export_format == 'pdf':
        return export_to_pdf(queryset, filename, 'custom_admin/export_pdf.html', title, headers, data_func)
    
    return redirect('custom_admin:dashboard')

@site_admin_required
def admin_dashboard(request):
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    recent_orders = Order.objects.select_related('customer').order_by('-created_at')[:5]
    recent_customers = Customer.objects.order_by('-created_at')[:5]
    low_stock_products = ProductVariant.objects.filter(stock_quantity__lt=F('reorder_threshold')).select_related('product')[:10]

    context = {
        'active_page': 'dashboard',
        'total_customers': total_customers,
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'recent_customers': recent_customers,
        'low_stock_variants': low_stock_products,
    }
    return render(request, 'custom_admin/dashboard.html', context)
    
@site_admin_required
def admin_pytest_reports(request):
    import os
    from django.conf import settings
    report_path = os.path.join(str(settings.BASE_DIR), 'htmlcov', 'index.html')
    exists = os.path.exists(report_path)
    
    context = {
        'active_page': 'pytest_reports',
        'report_exists': exists,
    }
    return render(request, 'custom_admin/pytest_reports.html', context)

@site_admin_required
def run_pytest_api(request):
    import subprocess
    import os
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST requests allowed.'}, status=405)
        
    try:
        # Get project root (parent of myproject/)
        # Using settings.BASE_DIR is more reliable
        from django.conf import settings
        root_dir = str(settings.BASE_DIR)
        
        # Create absolute report path to prevent directory drift
        report_dir = os.path.join(settings.BASE_DIR, 'htmlcov')
        
        # Run pytest. 
        # We use --cov-report=html to ensure the report is updated.
        # Note: In a production environment, this should be a background task (e.g. Celery).
        # For this project, we'll run it synchronously for simplicity.
        result = subprocess.run(
            ['pytest', f'--cov-report=html:{report_dir}'], 
            cwd=root_dir, 
            capture_output=True, 
            text=True,
            timeout=300 # 5 min timeout
        )
        
        if result.returncode == 0 or result.returncode == 1: # 1 means some tests failed, but it still ran
            return JsonResponse({
                'status': 'success', 
                'output': result.stdout,
                'exit_code': result.returncode
            })
        else:
            return JsonResponse({
                'status': 'error', 
                'message': 'Pytest encountered a system error.',
                'output': result.stderr
            }, status=500)
            
    except subprocess.TimeoutExpired:
        return JsonResponse({'status': 'error', 'message': 'Test suite timed out.'}, status=408)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@site_admin_required
def stream_pytest_api(request):
    import subprocess
    import os
    import sys

    # Get project root (myproject/)
    from django.conf import settings
    root_dir = str(settings.BASE_DIR)

    def stream_output():
        # Set PYTHONUNBUFFERED to see output in real time
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            ['pytest', '-v', '--color=yes'],
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )

        # Capture output for split reporting
        all_output = []
        for line in process.stdout:
            all_output.append(line)
            yield line

        process.wait()
        
        # Update dynamic reports (Success, Failure, etc.)
        try:
            update_split_reports("".join(all_output), root_dir)
        except Exception as e:
            yield f"\n[Warning] Could not update split reports: {str(e)}\n"
            
        yield "\n--- FINISHED ---"

    response = StreamingHttpResponse(stream_output(), content_type='text/plain')
    response['X-Accel-Buffering'] = 'no'
    return response
    
@site_admin_required
def admin_analytical_dashboard(request):
    """
    Renders the new advanced analytical dashboard.
    """
    categories = Category.objects.all()
    brands = Brand.objects.all()
    context = {
        'active_page': 'analytical_dashboard',
        'categories': categories,
        'brands': brands,
    }
    return render(request, 'custom_admin/analytical_dashboard.html', context)

def admin_login(request):
    # Check if already logged in via our custom session key
    if request.session.get('_site_admin_user_id'):
        return redirect('custom_admin:dashboard')

    # Basic throttling implementation using session
    attempts = request.session.get('login_attempts', 0)
    if attempts >= 5:
        messages.error(request, "Too many login attempts. Please try again later.")
        return render(request, 'custom_admin/login.html')

    if request.method == 'POST':
        username = request.POST.get('username')
        password  = request.POST.get('password')
        next_url = request.GET.get('next', 'custom_admin:dashboard')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if hasattr(user, 'site_admin_profile'):
                # We do NOT use auth_login(request, user) to prevent sharing session with django-admin
                request.session['_site_admin_user_id'] = user.id
                request.session['login_attempts'] = 0
                log_action(f"Admin: {user.username}", "Admin Login", "Successfully logged into Custom Admin.")
                return redirect(next_url)
            else:
                request.session['login_attempts'] = attempts + 1
                log_action(f"Guest ({user.username})", "Failed Admin Login", "Access Denied: Not a site administrator.")
                messages.error(request, "Access denied: Not a site administrator.")
        else:
            request.session['login_attempts'] = attempts + 1
            log_action(f"Guest ({username})", "Failed Admin Login", "Incorrect username or password.")
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'custom_admin/login.html')

def admin_logout(request):
    admin_id = request.session.get('_site_admin_user_id')
    user_info = "Admin"
    
    if admin_id:
        try:
            admin_user = User.objects.get(pk=admin_id)
            user_info = f"Admin: {admin_user.username}"
        except User.DoesNotExist:
            pass
        del request.session['_site_admin_user_id']
    
    log_action(user_info, "Admin Logout", "Admin logged out from Custom Admin.")
    messages.success(request, "You have been logged out from the admin panel.")
    return redirect('custom_admin:login')

@site_admin_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            # Update tracking information if provided
            order.tracking_number = request.POST.get('tracking_number', order.tracking_number)
            order.shipping_carrier = request.POST.get('shipping_carrier', order.shipping_carrier)
            order.carrier_url = request.POST.get('carrier_url', order.carrier_url)
            
            old_status = order.status
            order.status = new_status
            order.save()
            log_action(f"Admin: {request.site_admin.username}", "Updated Order Status & Tracking", f"Order #{order.id} | {old_status} -> {new_status}")
            messages.success(request, f"Order status and tracking information successfully updated.")
            return redirect('custom_admin:order_detail', order_id=order.id)
        else:
            messages.error(request, "Invalid order status.")
            
    items = OrderItem.objects.filter(order=order)
    context = {
        'active_page': 'orders', 
        'order': order, 
        'items': items,
        'status_choices': Order.ORDER_STATUS_CHOICES
    }
    return render(request, 'custom_admin/order_detail.html', context)

@site_admin_required
def admin_orders(request):
    query = request.GET.get('q')
    orders = Order.objects.select_related('customer').all().order_by('-created_at')
    
    if query:
        orders = orders.filter(Q(customer__full_name__icontains=query) | Q(id__icontains=query) | Q(customer__email__icontains=query))
        
    context = {'active_page': 'orders', 'orders': orders}
    return render(request, 'custom_admin/orders.html', context)

@site_admin_required
def admin_product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        formset = ProductImageFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()
            log_action(f"Admin: {request.site_admin.username}", "Created Product", f"Product: {product.full_name}")
            messages.success(request, "Product created successfully.")
            return redirect('custom_admin:products')
    else:
        form = ProductForm()
        formset = ProductImageFormSet()
    
    context = {'active_page': 'products', 'form': form, 'formset': formset, 'title': 'Add Product'}
    return render(request, 'custom_admin/product_form.html', context)

@site_admin_required
def admin_product_delete(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == 'POST':
        name = product.full_name
        product.delete()
        log_action(f"Admin: {request.site_admin.username}", "Deleted Product", f"Product: {name}")
        messages.success(request, f"Product '{name}' deleted.")
        return redirect('custom_admin:products')
    
    context = {'active_page': 'products', 'item': product, 'type': 'product'}
    return render(request, 'custom_admin/delete_confirm.html', context)

@site_admin_required
def admin_product_edit(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and formset.is_valid():
            form.save()
            images = formset.save()
            
            # Count changes for more detailed feedback
            added_count = len(formset.new_objects)
            deleted_count = len(formset.deleted_objects)
            
            msg = "Product updated successfully."
            if added_count > 0 or deleted_count > 0:
                parts = []
                if added_count > 0: parts.append(f"Added {added_count} image{'s' if added_count > 1 else ''}")
                if deleted_count > 0: parts.append(f"Removed {deleted_count} image{'s' if deleted_count > 1 else ''}")
                msg += f" ({', '.join(parts)})"
                
            log_action(f"Admin: {request.site_admin.username}", "Updated Product", f"Product: {product.full_name}")
            messages.success(request, msg)
            return redirect('custom_admin:products')
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)
    
    context = {'active_page': 'products', 'form': form, 'formset': formset, 'product': product, 'title': 'Edit Product'}
    return render(request, 'custom_admin/product_form.html', context)

@site_admin_required
def admin_products(request):
    query = request.GET.get('q')
    product_list = Product.objects.select_related('category_id', 'brand').order_by('brand__name', 'model_name')
    
    if query:
        product_list = product_list.filter(Q(brand__name__icontains=query) | Q(model_name__icontains=query) | Q(variants__sku__icontains=query)).distinct()
        
    paginator = Paginator(product_list, 10) # 10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    context = {'active_page': 'products', 'products': products}
    return render(request, 'custom_admin/products.html', context)

@site_admin_required
def admin_refresh_exchange_rates(request):
    """
    Force-refreshes the exchange rate cache.
    Accessible only to site admins from the custom admin dashboard.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST requests allowed.'}, status=405)
        
    try:
        from .services.currency_service import CurrencyService
        rates_data = CurrencyService.get_rates(force_refresh=True)
        log_action(f"Admin: {request.site_admin.username}", "Manual Exchange Rate Refresh", f"Base: {rates_data.get('base')} | Updated: {rates_data.get('timestamp')}")
        return JsonResponse({
            'status': 'success', 
            'message': 'Currency exchange rates successfully updated from the API.',
            'timestamp': rates_data.get('timestamp')
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

from .models import Attribute, AttributeValue, ProductVariant, VariantAttribute
from .forms import AttributeForm, AttributeValueFormSet, ProductVariantForm, VariantAttributeFormSet

@site_admin_required
def admin_attributes(request):
    attributes = Attribute.objects.prefetch_related('values').all().order_by('display_order', 'name')
    context = {'active_page': 'attributes', 'attributes': attributes}
    return render(request, 'custom_admin/attributes.html', context)

@site_admin_required
def admin_attribute_add(request):
    if request.method == 'POST':
        form = AttributeForm(request.POST)
        formset = AttributeValueFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            attr = form.save()
            formset.instance = attr
            formset.save()
            messages.success(request, f"Attribute '{attr.name}' added successfully.")
            return redirect('custom_admin:attributes')
    else:
        form = AttributeForm()
        formset = AttributeValueFormSet()
    
    context = {'form': form, 'formset': formset, 'title': 'Add Attribute', 'active_page': 'attributes'}
    return render(request, 'custom_admin/attribute_form.html', context)

@site_admin_required
def admin_attribute_edit(request, attribute_id):
    attr = get_object_or_404(Attribute, pk=attribute_id)
    if request.method == 'POST':
        form = AttributeForm(request.POST, instance=attr)
        formset = AttributeValueFormSet(request.POST, instance=attr)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f"Attribute '{attr.name}' updated.")
            return redirect('custom_admin:attributes')
    else:
        form = AttributeForm(instance=attr)
        formset = AttributeValueFormSet(instance=attr)
    
    context = {'form': form, 'formset': formset, 'title': 'Edit Attribute', 'active_page': 'attributes'}
    return render(request, 'custom_admin/attribute_form.html', context)

@site_admin_required
def admin_attribute_delete(request, attribute_id):
    attr = get_object_or_404(Attribute, pk=attribute_id)
    if request.method == 'POST':
        name = attr.name
        attr.delete()
        messages.success(request, f"Attribute '{name}' deleted.")
        return redirect('custom_admin:attributes')
    return render(request, 'custom_admin/delete_confirm.html', {'item': attr, 'type': 'attribute', 'active_page': 'attributes'})

@site_admin_required
def admin_variants(request):
    query = request.GET.get('q')
    variants = ProductVariant.objects.select_related('product').prefetch_related('attributes__attribute').all().order_by('-id')
    if query:
        variants = variants.filter(Q(sku__icontains=query) | Q(product__model_name__icontains=query))
    
    paginator = Paginator(variants, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'active_page': 'variants', 'variants': page_obj}
    return render(request, 'custom_admin/variants.html', context)

@site_admin_required
def admin_variant_add(request):
    product_id = request.GET.get('product_id')
    initial = {}
    if product_id:
        initial['product'] = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        form = ProductVariantForm(request.POST)
        attr_formset = VariantAttributeFormSet(request.POST)
        
        if form.is_valid() and attr_formset.is_valid():
            variant = form.save()
            attr_formset.instance = variant
            attr_formset.save()
            messages.success(request, f"Variant {variant.sku} added.")
            return redirect('custom_admin:variants')
    else:
        form = ProductVariantForm(initial=initial)
        attr_formset = VariantAttributeFormSet()
        
    context = {'form': form, 'attr_formset': attr_formset, 'title': 'Add Variant', 'active_page': 'variants'}
    return render(request, 'custom_admin/variant_form.html', context)

@site_admin_required
def admin_variant_edit(request, variant_id):
    variant = get_object_or_404(ProductVariant, pk=variant_id)
    if request.method == 'POST':
        form = ProductVariantForm(request.POST, instance=variant)
        attr_formset = VariantAttributeFormSet(request.POST, instance=variant)
        
        if form.is_valid() and attr_formset.is_valid():
            form.save()
            attr_formset.save()
            messages.success(request, f"Variant {variant.sku} updated.")
            return redirect('custom_admin:variants')
    else:
        form = ProductVariantForm(instance=variant)
        attr_formset = VariantAttributeFormSet(instance=variant)
        
    context = {'form': form, 'attr_formset': attr_formset, 'variant': variant, 'title': 'Edit Variant', 'active_page': 'variants'}
    return render(request, 'custom_admin/variant_form.html', context)

@site_admin_required
def admin_variant_delete(request, variant_id):
    variant = get_object_or_404(ProductVariant, pk=variant_id)
    if request.method == 'POST':
        sku = variant.sku
        variant.delete()
        messages.success(request, f"Variant {sku} deleted.")
        return redirect('custom_admin:variants')
    return render(request, 'custom_admin/delete_confirm.html', {'item': variant, 'type': 'variant', 'active_page': 'variants'})

def update_split_reports(output, root_dir):
    """
    Parses pytest -v output and generates passed_tests.html, failed_tests.html, etc.
    in the htmlcov directory.
    """
    import os
    import re

    report_dir = os.path.join(root_dir, 'htmlcov')
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    passed = []
    failed = []
    errors = []
    warnings = []
    
    # Track items to avoid duplicates
    seen_passed = set()
    seen_failed = set()
    seen_errors = set()

    lines = output.splitlines()
    
    # 1. Parse individual test results (PASSED, FAILED, etc.)
    for line in lines:
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        
        # Match pattern: path/to/test.py::test_name STATUS [PROGRESS%]
        # Example: myproject/myapp/tests/test_views.py::test_index PASSED [ 5%]
        match = re.search(r'^(.*?)\s+(PASSED|FAILED|ERROR|SKIPPED|XPASS|XFAIL)', clean_line)
        if match:
            test_id = match.group(1).split(' [')[0].strip()
            status = match.group(2)
            
            # Extract duration if present (usually at end of line if -v -v or similar)
            duration = "N/A"
            dur_match = re.search(r'in\s+([\d\.]+s)', clean_line)
            if dur_match:
                duration = dur_match.group(1)
            
            item = {'name': test_id, 'duration': duration}
            
            if status == 'PASSED':
                if test_id not in seen_passed:
                    passed.append(item)
                    seen_passed.add(test_id)
            elif status == 'FAILED':
                if test_id not in seen_failed:
                    failed.append(item)
                    seen_failed.add(test_id)
            elif status == 'ERROR':
                if test_id not in seen_errors:
                    errors.append(item)
                    seen_errors.add(test_id)
        
    # 2. Parse Warnings (usually in summary section)
    in_warnings_summary = False
    for line in lines:
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        if 'warnings summary' in clean_line.lower():
            in_warnings_summary = True
            continue
        if in_warnings_summary and (clean_line.startswith('===') or clean_line.startswith('---')):
            in_warnings_summary = False
            continue
            
        if in_warnings_summary:
            # Look for lines that look like test IDs
            if '::' in clean_line and not clean_line.startswith(' '):
                test_id = clean_line.strip()
                if test_id not in [w['name'] for w in warnings]:
                    warnings.append({'name': test_id, 'duration': 'Warning'})

    def generate_html(title, items, filename, color):
        html_content = f"""
        <html>
        <head>
            <title>{title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Fira+Code&display=swap" rel="stylesheet">
            <style>
                body {{ 
                    font-family: 'Inter', sans-serif; 
                    padding: 40px; 
                    background: #0f172a; 
                    color: #f1f5f9; 
                    line-height: 1.6; 
                    margin: 0;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                h1 {{ 
                    color: {color}; 
                    border-bottom: 2px solid {color}44; 
                    padding-bottom: 16px; 
                    margin-bottom: 40px; 
                    font-weight: 600; 
                    font-size: 2.5rem;
                }}
                .test-list {{
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }}
                .test-item {{ 
                    background: #1e293b; 
                    padding: 24px; 
                    border-radius: 16px; 
                    border-left: 6px solid {color}; 
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); 
                    transition: all 0.2s ease;
                }}
                .test-item:hover {{ 
                    transform: translateY(-2px);
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
                }}
                .test-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 0;
                    gap: 20px;
                }}
                .test-name {{ 
                    font-weight: 500; 
                    font-family: 'Fira Code', monospace; 
                    font-size: 0.95rem; 
                    color: #e2e8f0; 
                    word-break: break-all; 
                    flex: 1;
                }}
                .test-duration {{ 
                    font-size: 0.85rem; 
                    color: #94a3b8; 
                    font-weight: 600; 
                    background: #334155; 
                    padding: 4px 12px; 
                    border-radius: 9999px;
                    white-space: nowrap;
                }}
                .no-items {{ 
                    font-style: italic; 
                    color: #94a3b8; 
                    text-align: center; 
                    padding: 80px; 
                    background: #1e293b; 
                    border-radius: 16px;
                    font-size: 1.1rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{title} ({len(items)})</h1>
                <div class="test-list">
        """
        if not items:
            html_content += f'<p class="no-items">No test cases found in this category.</p>'
        else:
            for item in items:
                html_content += f"""
                <div class="test-item">
                    <div class="test-header">
                        <span class="test-name">{item['name']}</span>
                        <span class="test-duration">{item['duration']}</span>
                    </div>
                </div>
                """
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(report_dir, filename), 'w', encoding='utf-8') as f:
            f.write(html_content)

    generate_html("Passed Test Cases Report", passed, "passed_tests.html", "#4ade80")
    generate_html("Failed Test Cases Report", failed, "failed_tests.html", "#f87171")
    generate_html("System Errors Report", errors, "error_tests.html", "#ff4444")
    generate_html("Warning Test Cases Report", warnings, "warnings_tests.html", "#fbbf24")
