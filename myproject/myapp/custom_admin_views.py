from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from functools import wraps
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .models import Customer, Category, Product, Cart, Order, OrderItem, SiteAdmin
from .forms import CategoryForm, ProductForm

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
            form.save()
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
        category.delete()
        messages.success(request, f"Category '{category.name}' deleted.")
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
            messages.success(request, "Category updated successfully.")
            return redirect('custom_admin:categories')
    else:
        form = CategoryForm(instance=category)
    
    context = {'active_page': 'categories', 'form': form, 'category': category, 'title': 'Edit Category'}
    return render(request, 'custom_admin/category_form.html', context)

@site_admin_required
def admin_customers(request):
    customers = Customer.objects.order_by('-created_at')
    context = {'active_page': 'customers', 'customers': customers}
    return render(request, 'custom_admin/customers.html', context)

@site_admin_required
def admin_dashboard(request):
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    recent_orders = Order.objects.order_by('-created_at')[:5]
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
                return redirect(next_url)
            else:
                request.session['login_attempts'] = attempts + 1
                messages.error(request, "Access denied: Not a site administrator.")
        else:
            request.session['login_attempts'] = attempts + 1
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'custom_admin/login.html')

def admin_logout(request):
    # Only clear our specific session key, don't use auth_logout to avoid global logout
    if '_site_admin_user_id' in request.session:
        del request.session['_site_admin_user_id']
    messages.success(request, "You have been logged out from the admin panel.")
    return redirect('custom_admin:login')

@site_admin_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    items = OrderItem.objects.filter(order=order).select_related('product')
    context = {'active_page': 'orders', 'order': order, 'items': items}
    return render(request, 'custom_admin/order_detail.html', context)

@site_admin_required
def admin_orders(request):
    orders = Order.objects.order_by('-created_at')
    context = {'active_page': 'orders', 'orders': orders}
    return render(request, 'custom_admin/orders.html', context)

@site_admin_required
def admin_product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
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
        product.delete()
        messages.success(request, f"Product '{product.name}' deleted.")
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
            messages.success(request, "Product updated successfully.")
            return redirect('custom_admin:products')
    else:
        form = ProductForm(instance=product)
    
    context = {'active_page': 'products', 'form': form, 'product': product, 'title': 'Edit Product'}
    return render(request, 'custom_admin/product_form.html', context)

@site_admin_required
def admin_products(request):
    product_list = Product.objects.select_related('category_id').order_by('name')
    paginator = Paginator(product_list, 10) # 10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    context = {'active_page': 'products', 'products': products}
    return render(request, 'custom_admin/products.html', context)
