import pytest
import json
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.test import Client, RequestFactory
from django.utils import timezone
from datetime import timedelta
from django.contrib.sessions.middleware import SessionMiddleware
from myapp.models import (
    Category, Brand, Product, ProductVariant, Customer, Cart,
    Order, OrderItem, Wishlist, ProductReview, Coupon,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(client, **kwargs):
    """Set arbitrary keys on the client session."""
    client.get("/")          # ensure session is initialised
    s = client.session
    for k, v in kwargs.items():
        s[k] = v
    s.save()

# ===========================================================================
# VIEW TESTS
# ===========================================================================

@pytest.mark.django_db
class TestViews:
    """Consolidated test suite for all views.py logic and branches."""

    def test_pages_and_filters(self, client, product, category, brand):
        """Standard page rendering and faceted filtering."""
        pages = ['about', 'bestseller', 'faq', 'privacy_policy', 'support', 'terms', 'sitemap', 'warranty', 'returns', 'home', 'index']
        for page in pages:
            assert client.get(reverse(page)).status_code == 200
        
        url = reverse('shop')
        assert client.get(url, {'cid': category.id}).status_code == 200
        assert client.get(url, {'brand': brand.id}).status_code == 200
        assert client.get(url, {'q': product.model_name}).status_code == 200
        assert client.get(url, {'sort': 'Price, ASC'}).status_code == 200
        assert client.get(url, {'max_price': '1000'}).status_code == 200
        assert client.get(url, {'max_price': 'invalid'}).status_code == 200
        assert client.get(reverse('single', args=[product.id])).status_code == 200

    def test_auth_and_registration(self, client, customer):
        """Auth flows including login, registration, and duplicate email handling."""
        # 1. Authenticated user trying to access login/register (Branch coverage)
        _make_session(client, email=customer.email)
        assert client.get(reverse('login')).status_code == 302
        assert client.get(reverse('register')).status_code == 302
        
        # Logout
        client.get(reverse('logout'))
        assert 'email' not in client.session
        
        # 2. Registration (Success and Failure)
        client.post(reverse('register'), {
            'name': 'New', 'email': 'new@e.com', 'password': 'p', 'confirm_password': 'p'
        })
        assert Customer.objects.filter(email='new@e.com').exists()
        
        # 3. Duplicate Email handle
        response = client.post(reverse('register'), {
            'name': 'Dup', 'email': customer.email, 'password': 'p', 'confirm_password': 'p'
        })
        assert response.status_code == 200 

    def test_password_reset_logic(self, client, customer):
        """Forgot and reset password flows with surgical branch coverage."""
        url_forgot = reverse('forgot_password')
        client.post(url_forgot, {'email': customer.email})
        otp = client.session['reset_otp']
        
        url_reset = reverse('reset_password')
        # 1. Invalid OTP
        client.post(url_reset, {'email': customer.email, 'otp': '0000', 'new_password': 'p', 'confirm_password': 'p'})
        # 2. Email mismatch
        client.post(url_reset, {'email': 'wrong@e.com', 'otp': otp, 'new_password': 'p', 'confirm_password': 'p'})
        # 3. Successful Reset (Hits success branches)
        _make_session(client, reset_email=customer.email, reset_otp=otp, reset_otp_time=time.time())
        # Ensure email is NOT in session to hit the assignment branch (line 773)
        client.get(reverse('logout')) 
        _make_session(client, reset_email=customer.email, reset_otp=otp, reset_otp_time=time.time())
        client.post(url_reset, {'email': customer.email, 'otp': str(otp), 'new_password': 'new', 'confirm_password': 'new'})
        customer.refresh_from_db()
        assert customer.password == 'new'

    def test_cart_management_surgical(self, client, customer, variant):
        """Detailed cart operations including stock checks and update actions."""
        _make_session(client, email=customer.email)
        url_add = reverse('add_to_cart', args=[variant.product.id])
        
        # Initial Add
        client.post(url_add, {'variant_id': variant.id, 'qty': 1})
        # Add existing
        client.post(url_add, {'variant_id': variant.id, 'qty': 1})
        cart_item = Cart.objects.get(customer=customer, variant=variant)
        assert cart_item.quantity == 2
        
        # Value Error in qty (973)
        client.get(url_add, {'qty': 'X', 'variant_id': variant.id})
        
        # Stock Limit Error (1010)
        variant.stock_quantity = 2; variant.save()
        client.post(url_add, {'variant_id': variant.id, 'qty': 10}) 
        
        # Update Actions (1076, 1078)
        client.get(reverse('update_cart', args=[cart_item.id, 'increase']))
        client.get(reverse('update_cart', args=[cart_item.id, 'decrease']))
        client.get(reverse('update_cart', args=[cart_item.id, 'invalid']))
        client.get(reverse('update_cart', args=[cart_item.id, 'remove']))
        # Unauth redirect (1065)
        client.get(reverse('logout'))
        assert client.get(reverse('update_cart', args=[1, 'increase'])).status_code == 302

    def test_checkout_and_coupons(self, client, customer, variant, coupon):
        """Checkout prerequisites, address validation, and coupon lifecycle."""
        _make_session(client, email=customer.email, checkout_allowed=True)
        Cart.objects.create(customer=customer, variant=variant, quantity=1)
        
        # Coupon Apply (1442, 1450)
        url_apply = reverse('apply_coupon')
        client.post(url_apply, "{invalid", content_type='application/json')
        client.post(url_apply, json.dumps({'code': coupon.code}), content_type='application/json')
        client.post(url_apply, json.dumps({'code': coupon.code}), content_type='application/json') # already applied
        
        # Valid coupon branch in checkout
        client.get(reverse('checkout'))
        
        # Address validation fail (Redirects to account)
        client.post(reverse('checkout'), {'payment_method': 'Delivery'})
        
        # Success Checkout
        customer.address = "A"; customer.town_city="C"; customer.state="S"; customer.country="C"; customer.postcode_zip="1"
        customer.save()
        with patch('myapp.views.log_action'):
            client.post(reverse('checkout'), {'payment_method': 'Delivery'})
        assert Order.objects.filter(customer=customer).exists()

    def test_my_account_tabs_and_filters(self, client, customer):
        """Account dashboard with all filter branches (date range, search, status)."""
        _make_session(client, email=customer.email)
        url = reverse('my_account')
        # Test filters (588, 594, 605)
        client.get(url, {'tab': 'dashboard'})
        client.get(url, {'tab': 'orders', 'date_range': '1y', 'status': 'Pending', 'q': 'query'})
        # Test profile Update
        client.post(url + "?tab=profile", {'full_name': 'N', 'email': customer.email})

    def test_ratings_exhaustive(self, client, product, customer):
        """Product ratings with session persistence, duplicate checks, and guest branches."""
        url_get = reverse('get_rating', args=[product.id])
        url_sub = reverse('submit_rating', args=[product.id])
        
        # Get Rating (Guest Ident by IP) (1157)
        with patch('myapp.views.get_client_ip', return_value='9.9.9.9'):
            ProductReview.objects.create(product=product, rating=5, review_text='X', ip_address='9.9.9.9')
            client.get(url_get)
        
        # Submit Rating (Invalid JSON / Invalid Rating) (1204, 1209)
        _make_session(client, email=customer.email)
        client.post(url_sub, "X", content_type='application/json')
        client.post(url_sub, json.dumps({'rating': 0}), content_type='application/json')
        
        # Success (1216-1217)
        ProductReview.objects.all().delete()
        client.post(url_sub, json.dumps({'rating': 5, 'review_text': 'G'}), content_type='application/json')
        
        # Duplicate check (1185, 1190)
        client.post(url_sub, json.dumps({'rating': 5, 'review_text': 'G'}), content_type='application/json')
        
        # Session Duplicate (1196)
        client.get(reverse('logout'))
        client.get('/') # Init session
        client.post(url_sub, json.dumps({'rating': 5, 'review_text': 'G'}), content_type='application/json')
        client.post(url_sub, json.dumps({'rating': 5, 'review_text': 'G'}), content_type='application/json')

    def test_order_consequences(self, client, customer, variant, order):
        """Buy again, cancel order, return order, and detail views (662, 671)."""
        _make_session(client, email=customer.email)
        OrderItem.objects.create(order=order, variant=variant, quantity=1, snapshot_product_name="X")
        ProductReview.objects.create(product=variant.product, customer=customer, rating=5, review_text="X", ip_address="0")
        
        # Buy Again
        client.get(reverse('buy_again', args=[order.id]))
        # Cancel (Pending)
        client.get(reverse('cancel_order', args=[order.id]))
        # Return (not delivered)
        client.get(reverse('return_order', args=[order.id]))
        # Detail view with review coverage
        client.get(reverse('order_detail', args=[order.id]))

    def test_wishlist_and_utilities(self, client, customer, variant, order):
        """Wishlist toggling and utility views like invoices and comparison."""
        _make_session(client, email=customer.email)
        url_wish = reverse('toggle_wishlist', args=[variant.product.id])
        # Add Toggles (1052)
        client.post(url_wish, {'variant_id': variant.id})
        client.post(url_wish, {'variant_id': variant.id})
        
        # Comparison
        client.get(reverse('compare'), {'ids': f"{variant.product.id}"})
        # Invoice (Playwright)
        with patch('myapp.views.sync_playwright'):
            assert client.get(reverse('download_invoice', args=[order.id])).status_code == 200
        # Payment Success (1426)
        client.get(reverse('payment_success'), {'order_id': order.id})

@pytest.mark.django_db
class TestInfrastructureViews:
    """Tests for middleware handlers and API endpoints."""
    def test_error_handlers(self, rf):
        from myapp.views import error_404, error_500
        request = rf.get("/")
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        assert error_404(request).status_code == 404
        assert error_500(request).status_code == 500

    def test_apis(self, client):
        assert client.get(reverse('exchange_rates')).status_code == 200