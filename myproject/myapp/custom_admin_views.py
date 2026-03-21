from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from functools import wraps
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .models import Customer, Category, Product, Cart, Order, OrderItem, SiteAdmin, Brand
from .forms import CategoryForm, ProductForm, BrandForm
from .logger import log_action
from .exports import export_to_csv, export_to_excel, export_to_word, export_to_pdf
from datetime import datetime

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
        queryset = OrderItem.objects.select_related('order', 'product').all().order_by('-order__created_at')
        filename = f"order_details_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Order Details (Line Items)"
        headers = ['Order ID', 'Product', 'SKU', 'Quantity', 'Unit Price', 'Subtotal']
        def data_func(obj):
            return [obj.order.id, obj.product.name, obj.product.sku or 'N/A', obj.quantity, f"${obj.price}", f"${obj.line_total()}"]

    elif module == 'products':
        queryset = Product.objects.select_related('category_id', 'brand').all().order_by('brand__name', 'model_name')
        filename = f"products_{datetime.now().strftime('%Y-%m-%d')}"
        title = "Product Listing"
        headers = ['ID', 'Brand', 'Model', 'Variant', 'SKU', 'Category', 'Price', 'Stock', 'Status']
        def data_func(obj):
            status = 'In Stock' if obj.stock_quantity > 0 else 'Out of Stock'
            return [obj.id, obj.brand.name if obj.brand else 'N/A', obj.model_name or 'N/A', obj.variant_specs or 'N/A', obj.sku or 'N/A', obj.category_id.name, f"₹{obj.price}", obj.stock_quantity, status]
            
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
            queryset = queryset.filter(Q(full_name__icontains=query) | Q(id__icontains=query))
        elif module == 'products':
            queryset = queryset.filter(Q(brand__name__icontains=query) | Q(model_name__icontains=query) | Q(sku__icontains=query))

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
    low_stock_products = Product.objects.filter(stock_quantity__lte=5).order_by('stock_quantity')

    context = {
        'active_page': 'dashboard',
        'total_customers': total_customers,
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'recent_customers': recent_customers,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'custom_admin/dashboard.html', context)

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
            
    items = OrderItem.objects.filter(order=order).select_related('product')
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
        if form.is_valid():
            product = form.save()
            log_action(f"Admin: {request.site_admin.username}", "Created Product", f"Product: {product.full_name}")
            messages.success(request, "Product created successfully.")
            return redirect('custom_admin:products')
    else:
        form = ProductForm()
    
    context = {'active_page': 'products', 'form': form, 'title': 'Add Product'}
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
        if form.is_valid():
            form.save()
            log_action(f"Admin: {request.site_admin.username}", "Updated Product", f"Product: {product.full_name}")
            messages.success(request, "Product updated successfully.")
            return redirect('custom_admin:products')
    else:
        form = ProductForm(instance=product)
    
    context = {'active_page': 'products', 'form': form, 'product': product, 'title': 'Edit Product'}
    return render(request, 'custom_admin/product_form.html', context)

@site_admin_required
def admin_products(request):
    query = request.GET.get('q')
    product_list = Product.objects.select_related('category_id', 'brand').order_by('brand__name', 'model_name')
    
    if query:
        product_list = product_list.filter(Q(brand__name__icontains=query) | Q(model_name__icontains=query) | Q(sku__icontains=query))
        
    paginator = Paginator(product_list, 10) # 10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    context = {'active_page': 'products', 'products': products}
    return render(request, 'custom_admin/products.html', context)
