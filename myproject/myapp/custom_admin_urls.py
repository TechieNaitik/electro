from django.urls import path
from . import custom_admin_views as views
from . import admin_api_views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('', views.admin_dashboard, name='dashboard'),
    path('analytical/', views.admin_analytical_dashboard, name='analytical_dashboard'),
    path('customers/', views.admin_customers, name='customers'),
    
    # Products
    path('products/', views.admin_products, name='products'),
    path('products/add/', views.admin_product_add, name='product_add'),
    path('products/edit/<int:product_id>/', views.admin_product_edit, name='product_edit'),
    path('products/delete/<int:product_id>/', views.admin_product_delete, name='product_delete'),
    
    # Categories
    path('categories/', views.admin_categories, name='categories'),
    path('categories/add/', views.admin_category_add, name='category_add'),
    path('categories/edit/<int:category_id>/', views.admin_category_edit, name='category_edit'),
    path('categories/delete/<int:category_id>/', views.admin_category_delete, name='category_delete'),
    
    # Brands
    path('brands/', views.admin_brands, name='brands'),
    path('brands/add/', views.admin_brand_add, name='brand_add'),
    path('brands/edit/<int:brand_id>/', views.admin_brand_edit, name='brand_edit'),
    path('brands/delete/<int:brand_id>/', views.admin_brand_delete, name='brand_delete'),
    
    # Orders
    path('orders/', views.admin_orders, name='orders'),
    path('orders/<int:order_id>/', views.admin_order_detail, name='order_detail'),
    
    # Export
    path('export/', views.admin_export, name='export'),
    
    # API Endpoints
    path('api/dashboard/stats/', admin_api_views.dashboard_stats_api, name='api_dashboard_stats'),
]
