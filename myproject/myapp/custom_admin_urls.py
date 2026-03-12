from django.urls import path
from . import custom_admin_views as views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('customers/', views.admin_customers, name='customers'),
    path('products/', views.admin_products, name='products'),
    path('categories/', views.admin_categories, name='categories'),
    path('orders/', views.admin_orders, name='orders'),
    path('orders/<int:order_id>/', views.admin_order_detail, name='order_detail'),
]
