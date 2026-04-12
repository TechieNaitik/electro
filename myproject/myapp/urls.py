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
    # =========================================================================
    #  PAGE URLs  —  These render full HTML pages
    # =========================================================================
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('bestseller', views.bestseller, name='bestseller'),
    path('cart', views.cart, name='cart'),
    path('category/<int:cid>/', views.category_products, name='category_products'),
    path('checkout', views.checkout, name='checkout'),
    path('compare/', views.compare_view, name='compare'),
    path('contact', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('forgot_password', views.forgot_password, name='forgot_password'),
    path('help/', views.help, name='help'),
    path('home', views.home, name='home'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('returns/', views.returns, name='returns'),
    path('warranty/', views.warranty, name='warranty'),
    path('proceed-to-checkout/', views.proceed_to_checkout, name='proceed_to_checkout'),
    path('register', views.register, name='register'),
    path('reset_password', views.reset_password, name='reset_password'),
    path('shop/', views.shop, name='shop'),
    path('shop/<int:cid>/', views.shop, name='shop_category'),
    path('single/<int:pid>/', views.single, name='single'),
    path('sitemap/', views.sitemap, name='sitemap'),
    path('support/', views.support, name='support'),
    path('terms/', views.terms, name='terms'),
    path('wishlist', views.wishlist, name='wishlist'),
    path('my-account/', views.my_account, name='my_account'),
    path('order-history/', views.order_history, name='order_history'),
    path('order-detail/<int:oid>/', views.order_detail, name='order_detail'),
    path('buy-again/<int:oid>/', views.buy_again, name='buy_again'),
    path('cancel-order/<int:oid>/', views.cancel_order, name='cancel_order'),
    path('return-order/<int:oid>/', views.return_order, name='return_order'),
    path('download-invoice/<int:oid>/', views.download_invoice, name='download_invoice'),

    # =========================================================================
    #  AJAX URLs  —  These return JSON responses
    # =========================================================================
    path('add-to-cart/<int:pid>/', views.add_to_cart, name='add_to_cart'),
    path('toggle-wishlist/<int:pid>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('update-cart/<int:cid>/<str:action>/', views.update_cart, name='update_cart'),
    path('cart/apply-coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('cart/remove-coupon/', views.remove_coupon_view, name='remove_coupon'),

    # Rating System API
    path('api/ratings/<int:pid>/', views.get_product_rating, name='get_rating'),
    path('api/ratings/submit/<int:pid>/', views.submit_product_rating, name='submit_rating'),

    # Razorpay Integration URLs
    path('api/create-razorpay-order', views.create_razorpay_order, name='create_razorpay_order'),
    path('api/verify-razorpay-payment', views.verify_razorpay_payment, name='verify_razorpay_payment'),

    path('api/exchange-rates/', views.exchange_rates, name='exchange_rates'),
    path('payment-success', views.payment_success, name='payment_success'),

]
