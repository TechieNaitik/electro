"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('home', views.home, name='home'),
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
    path('shop/', views.shop, name='shop'),
    path('shop/<int:cid>/', views.shop, name='shop_category'),
    path('single/<int:pid>/', views.single, name='single'),
    path('cart', views.cart, name='cart'),
    path('checkout', views.checkout, name='checkout'),
    path('contact', views.contact, name='contact'),
    path('error', views.error, name='error'),
    path('bestseller', views.bestseller, name='bestseller'),
    path('logout', views.logout, name='logout'),
    path('forgot_password', views.forgot_password, name='forgot_password'),
    path('reset_password', views.reset_password, name='reset_password'),
    path('category/<int:cid>/', views.category_products, name='category_products'),
    path('about/', views.about, name='about'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms, name='terms'),
    path('sitemap/', views.sitemap, name='sitemap'),
    path('faq/', views.faq, name='faq'),
    path('add-to-cart/<int:pid>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:cid>/<str:action>/', views.update_cart, name='update_cart'),
]
