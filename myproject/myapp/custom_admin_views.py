from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count
from .models import Customer, Category, Product, Cart, Order, OrderItem


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# Customers
# ─────────────────────────────────────────────────────────────────────────────
def admin_customers(request):
    customers = Customer.objects.order_by('-created_at')
    context = {'active_page': 'customers', 'customers': customers}
    return render(request, 'custom_admin/customers.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Products
# ─────────────────────────────────────────────────────────────────────────────
def admin_products(request):
    products = Product.objects.select_related('category_id').order_by('name')
    context = {'active_page': 'products', 'products': products}
    return render(request, 'custom_admin/products.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────
def admin_categories(request):
    categories = Category.objects.order_by('id')
    context = {'active_page': 'categories', 'categories': categories}
    return render(request, 'custom_admin/categories.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Orders
# ─────────────────────────────────────────────────────────────────────────────
def admin_orders(request):
    orders = Order.objects.order_by('-created_at')
    context = {'active_page': 'orders', 'orders': orders}
    return render(request, 'custom_admin/orders.html', context)


def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    items = OrderItem.objects.filter(order=order).select_related('product')
    context = {'active_page': 'orders', 'order': order, 'items': items}
    return render(request, 'custom_admin/order_detail.html', context)
