from django.urls import path
from . import custom_admin_views as views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('', views.admin_dashboard, name='dashboard'),
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
    
    # Orders
    path('orders/', views.admin_orders, name='orders'),
    path('orders/<int:order_id>/', views.admin_order_detail, name='order_detail'),
    
    # Export
    path('export/', views.admin_export, name='export'),
]
