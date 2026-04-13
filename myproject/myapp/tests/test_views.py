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

    def test_get_client_ip_branches(self, rf):
        from myapp.views import get_client_ip
        # 1. Test with X-Forwarded-For (Hits the 'if' branch)
        request = rf.get('/', HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8')
        assert get_client_ip(request) == '1.2.3.4'
        
        # 2. Test with REMOTE_ADDR (Hits the 'else' branch)
        request = rf.get('/', REMOTE_ADDR='9.9.9.9')
        assert get_client_ip(request) == '9.9.9.9'

    def test_legacy_redirect_views(self, client):
        """Tests views that simply redirect to the account tabs."""
        assert client.get(reverse('order_history')).status_code == 302
        assert client.get(reverse('wishlist')).status_code == 302
@pytest.mark.django_db
class TestRemoveCouponView:
    def test_remove_coupon(self, client, customer):
        _make_session(client, email=customer.email, coupon_id=1)
        # Fixed: Use 'remove_coupon' as the correct URL name
        response = client.post(reverse('remove_coupon'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert 'coupon_id' not in client.session

@pytest.mark.django_db
class TestAddToCartAjax:
    def test_add_to_cart_no_variant_multi_variant_ajax(self, client, customer, product):
        """Test adding to cart without variant_id for a product with multiple variants."""
        _make_session(client, email=customer.email)
        # Create at least 2 active variants to trigger the 'multi-variant' error branch
        from myapp.models import ProductVariant
        ProductVariant.objects.create(product=product, sku="V1_unique", price=100, stock_quantity=10, is_active=True)
        ProductVariant.objects.create(product=product, sku="V2_unique", price=200, stock_quantity=10, is_active=True)
        
        response = client.post(
            reverse('add_to_cart', args=[product.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        # Should return error because variant_id is missing and multiple variants exist
        assert response.json()['status'] == 'error'
        assert "Please select a variant" in response.json()['message']

@pytest.mark.django_db
class TestZeroCoverageViews:
    """Tests for views that originally had zero coverage."""

    def test_cart_view(self, client, customer, variant, coupon):
        """Covers all branches in cart view: unauth, empty cart, valid/invalid coupons."""
        url = reverse('cart')
        
        # 1. Unauthenticated branch
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('login')
        
        # Authenticate
        _make_session(client, email=customer.email)
        
        # 2. Authenticated, empty cart
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['cart_count'] == 0
        
        # Add item to cart
        from myapp.models import Cart
        Cart.objects.create(customer=customer, variant=variant, quantity=1)
        
        # 3. Authenticated, valid coupon
        # Assuming coupon is valid (min_amount <= total)
        coupon.min_amount = Decimal('0.00')
        coupon.save()
        _make_session(client, email=customer.email, coupon_id=coupon.id)
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['applied_coupon'] == coupon
        assert response.context['discount'] > 0
        
        # 4. Authenticated, invalid coupon
        coupon.active = False # make it invalid
        coupon.save()
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['applied_coupon'] is None
        assert client.session.get('coupon_id') is None

    def test_category_products_view(self, client, category, product):
        """Covers all products (cid=0) and specific category products branches."""
        # 1. cid = 0 (all products)
        url_all = reverse('category_products', args=[0])
        response = client.get(url_all)
        assert response.status_code == 200
        assert product in response.context['products']
        
        # 2. cid > 0 (specific category)
        url_cat = reverse('category_products', args=[category.id])
        response = client.get(url_cat)
        assert response.status_code == 200
        assert response.context['selected_category'] == category

    def test_contact_view(self, client):
        """Covers GET and POST branches of contact view."""
        url = reverse('contact')
        
        # 1. GET request
        response = client.get(url)
        assert response.status_code == 200
        
        # 2. POST request
        response = client.post(url, {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Hello',
            'message': 'This is a test message'
        })
        assert response.status_code == 302
        assert response.url == url

    def test_proceed_to_checkout_view(self, client, customer):
        """Covers auth checks and session flag setting."""
        url = reverse('proceed_to_checkout')
        
        # 1. Unauthenticated branch
        response = client.get(url)
        assert response.status_code == 302
        
        # 2. Authenticated branch
        _make_session(client, email=customer.email)
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('checkout')
        assert client.session.get('checkout_allowed') is True

    def test_help_view(self, client):
        """Covers help view rendering."""
        url = reverse('help')
        response = client.get(url)
        assert response.status_code == 200

@pytest.mark.django_db
class TestLowCoverageViews:
    """Tests for views that had low coverage, filling in missing branches."""

    def test_login_view(self, client, customer):
        """Covers all missing branches of the login view."""
        url = reverse('login')
        
        # 1. Missing email
        response = client.post(url, {'email': '', 'password': 'test'})
        assert response.status_code == 200
        assert b"Please enter your email" in response.content

        # 2. Missing password
        response = client.post(url, {'email': 'test@example.com', 'password': ''})
        assert response.status_code == 200
        assert b"Please enter your password" in response.content

        # 3. Invalid email or password
        response = client.post(url, {'email': 'test@example.com', 'password': 'wrong'})
        assert response.status_code == 200
        assert b"Invalid email or password" in response.content

        # 4. Successful login
        with patch('myapp.views.log_action'):
            response = client.post(url, {'email': customer.email, 'password': customer.password})
        assert response.status_code == 302
        assert response.url == reverse('home')
        assert client.session.get('email') == customer.email

        # 5. Already logged in branch
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('home')

    def test_return_order_view(self, client, customer, order):
        """Covers returning eligible and ineligible orders."""
        url = reverse('return_order', args=[order.id])

        # 1. Unauthenticated
        response = client.get(url)
        assert response.status_code == 302
        
        # Authenticate
        _make_session(client, email=customer.email)

        # 2. Order not eligible (status != Delivered)
        order.status = 'Pending'
        order.save()
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('order_detail', args=[order.id])

        # 3. Order is eligible (status == Delivered)  <-- coverage was missing here
        order.status = 'Delivered'
        order.save()
        response = client.get(url)
        assert response.status_code == 302
        order.refresh_from_db()
        assert order.status == 'Returned'

    def test_forgot_password_view(self, client, customer):
        """Covers missing branches in forgot password view."""
        url = reverse('forgot_password')
        
        # 1. Missing email
        response = client.post(url, {'email': ''})
        assert response.status_code == 200
        assert b"Please enter your email." in response.content
        
        # 2. Invalid email format
        response = client.post(url, {'email': 'invalid-email'})
        assert response.status_code == 200
        assert b"Please enter a valid email address." in response.content

        # 3. No account found
        response = client.post(url, {'email': 'notfound@example.com'})
        assert response.status_code == 200
        assert b"No account found with this email." in response.content

        # 4. Exception in send_mail
        with patch('myapp.views.send_mail', side_effect=Exception('Mail error')):
            response = client.post(url, {'email': customer.email})
        assert response.status_code == 200
        assert b"Failed to send OTP. Please check email configuration." in response.content

    def test_reset_password_view(self, client, customer):
        """Covers missing branches in reset password view."""
        url = reverse('reset_password')
        
        # 1. No reset_email in session
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('forgot_password')

        # 2. Missing fields
        _make_session(client, reset_email=customer.email)
        response = client.post(url, {'email': customer.email, 'otp': '123456'}) # Missing new_password
        assert response.status_code == 200
        assert b"All fields are required." in response.content

        # 3. Passwords do not match
        _make_session(client, reset_email=customer.email, reset_otp='123456')
        response = client.post(url, {
            'email': customer.email, 
            'otp': '123456', 
            'new_password': 'pass', 
            'confirm_password': 'diff'
        })
        assert response.status_code == 200
        assert b"Passwords do not match." in response.content

        # 4. OTP Expired (> 300s)
        _make_session(client, reset_email=customer.email, reset_otp='123456', reset_otp_time=time.time() - 400)
        response = client.post(url, {
            'email': customer.email, 
            'otp': '123456', 
            'new_password': 'pass', 
            'confirm_password': 'pass'
        })
        assert response.status_code == 200
        assert b"OTP expired." in response.content

        # 5. Successful reset and logging out the existing session
        _make_session(client, email=customer.email, name=customer.full_name, reset_email=customer.email, reset_otp='123456', reset_otp_time=time.time())
        response = client.post(url, {
            'email': customer.email, 
            'otp': '123456', 
            'new_password': 'newpass', 
            'confirm_password': 'newpass'
        })
        assert response.status_code == 302
        assert response.url == reverse('login')
        assert 'email' not in client.session # User gets logged out

        # 6. GET request (success branch loading template)
        _make_session(client, reset_email=customer.email)
        response = client.get(url)
        assert response.status_code == 200

    def test_register_view(self, client):
        """Covers missing branches in register view."""
        url = reverse('register')
        
        # 1. GET request
        response = client.get(url)
        assert response.status_code == 200
        
        # 2. Missing fields
        response = client.post(url, {'name': 'Test', 'email': 'test@example.com'}) # missing passwords
        assert response.status_code == 200
        assert b"All fields are required." in response.content
        
        # 3. Passwords do not match
        response = client.post(url, {
            'name': 'Test', 
            'email': 'test@example.com', 
            'password': 'pass', 
            'confirm_password': 'diff'
        })
        assert response.status_code == 200
        assert b"Passwords do not match." in response.content

@pytest.mark.django_db
class TestRemainingCoverage:
    """Covers tiny dangling branches to push coverage to 100%."""
    
    def test_buy_again_branches(self, client, customer, order, variant):
        url = reverse('buy_again', args=[order.id])
        # Unauth
        assert client.get(url).status_code == 302
        
        # Test stock <= cart_item.quantity
        from myapp.models import Cart
        Cart.objects.create(customer=customer, variant=variant, quantity=5)
        variant.stock_quantity = 3
        variant.save()
        _make_session(client, email=customer.email)
        
        from myapp.models import OrderItem
        OrderItem.objects.create(order=order, variant=variant, quantity=1, snapshot_product_name="X")
        response = client.get(url)
        assert response.status_code == 302
        
    def test_cancel_order_unauth_and_ineligible(self, client, order, customer):
        url = reverse('cancel_order', args=[order.id])
        assert client.get(url).status_code == 302
        _make_session(client, email=customer.email)
        order.status = 'Delivered'
        order.save()
        assert client.get(url).status_code == 302
        
    def test_checkout_branches(self, client, customer, variant, coupon):
        url = reverse('checkout')
        assert client.get(url).status_code == 302
        _make_session(client, email=customer.email)
        assert client.get(url).status_code == 302 # No checkout_allowed
        _make_session(client, email=customer.email, checkout_allowed=True)
        assert client.get(url).status_code == 302 # empty cart

        from myapp.models import Cart
        Cart.objects.create(customer=customer, variant=variant, quantity=1)
        # Invalid coupon
        coupon.active = False
        coupon.save()
        _make_session(client, email=customer.email, checkout_allowed=True, coupon_id=coupon.id)
        assert client.get(url).status_code == 200

        # Insufficient stock POST
        variant.stock_quantity = 0
        variant.save()
        customer.address = "A"; customer.town_city="C"; customer.state="S"; customer.country="C"; customer.postcode_zip="1"
        customer.save()
        assert client.post(url, {'payment_method': 'Delivery'}).status_code == 302

        # Final validate fail
        variant.stock_quantity = 10
        variant.save()
        coupon.active = True
        coupon.save()
        with patch('myapp.models.Coupon.is_valid', return_value=(False, "Nope")):
            assert client.post(url, {'payment_method': 'Delivery'}).status_code == 302
            
    def test_download_invoice_admin(self, client, order):
        with patch('myapp.views.sync_playwright'):
            _make_session(client, _site_admin_user_id=1)
            assert client.get(reverse('download_invoice', args=[order.id])).status_code == 200
            
    def test_my_account_branches(self, client, customer):
        url = reverse('my_account')
        assert client.get(url).status_code == 302
        _make_session(client, email=customer.email)
        assert client.get(url, {'tab': 'orders', 'date_range': '30d'}).status_code == 200
        assert client.get(url, {'tab': 'orders', 'date_range': '3m'}).status_code == 200
        assert client.get(url, {'tab': 'orders', 'date_range': '6m'}).status_code == 200
        assert client.get(url, {'tab': 'orders', 'q': 'query'}).status_code == 200
        assert client.get(url, {'tab': 'wishlist'}).status_code == 200
        from myapp.models import Customer
        Customer.objects.create(full_name='Other', email='other@e.com', password='p')
        response = client.post(url + "?tab=profile", {'email': 'other@e.com'})
        assert response.status_code == 200

    def test_order_detail_unauth_and_mask(self, client, customer, order):
        url = reverse('order_detail', args=[order.id])
        assert client.get(url).status_code == 302
        _make_session(client, email=customer.email)
        order.payment_method = "Visa"
        order.save()
        assert client.get(url).status_code == 200

    def test_shop_errors(self, client):
        url = reverse('shop')
        assert client.get(url, {'cid': 'invalid'}).status_code == 200
        assert client.get(url, {'cid': 9999}).status_code == 200 # Category.DoesNotExist
        assert client.get(url, {'brand': 'invalid'}).status_code == 200

    def test_single_reviews(self, client, product, customer):
        url = reverse('single', args=[product.id])
        _make_session(client, email='missing@e.com')
        assert client.get(url).status_code == 200
        
        # To get a session key, we make a get request
        client.get('/')
        session_key = client.session.session_key
        from myapp.models import ProductReview
        ProductReview.objects.create(product=product, customer=customer, rating=5, review_text="A", session_key=session_key, ip_address="127.0.0.1")
        assert client.get(url).status_code == 200

    def test_add_to_cart_ajax_unauth(self, client, variant):
        url = reverse('add_to_cart', args=[variant.product.id])
        res = client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'
        assert client.post(url).status_code == 302 # Standard
        
    def test_add_to_cart_single_variant_fallback(self, client, customer, product):
        from myapp.models import ProductVariant
        product.variants.all().delete()
        ProductVariant.objects.create(product=product, sku="V1", price=100, stock_quantity=10, is_active=True)
        _make_session(client, email=customer.email)
        assert client.post(reverse('add_to_cart', args=[product.id])).status_code == 302

    def test_add_to_cart_missing_variant(self, client, customer, product):
        from myapp.models import ProductVariant
        product.variants.all().delete()
        ProductVariant.objects.create(product=product, sku="V1", price=100, stock_quantity=10, is_active=True)
        ProductVariant.objects.create(product=product, sku="V2", price=100, stock_quantity=10, is_active=True)
        _make_session(client, email=customer.email)
        assert client.post(reverse('add_to_cart', args=[product.id])).status_code == 302
        res = client.post(reverse('add_to_cart', args=[product.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'

    def test_add_to_cart_invalid_variant(self, client, customer, product):
        _make_session(client, email=customer.email)
        assert client.post(reverse('add_to_cart', args=[product.id]), {'variant_id': 9999}).status_code == 302
        res = client.post(reverse('add_to_cart', args=[product.id]), {'variant_id': 9999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'

    def test_add_to_cart_ajax_success(self, client, customer, variant):
        _make_session(client, email=customer.email)
        res = client.post(reverse('add_to_cart', args=[variant.product.id]), {'variant_id': variant.id, 'qty': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'success'

    def test_add_to_cart_ajax_stock_error(self, client, customer, variant):
        variant.stock_quantity = 0
        variant.save()
        _make_session(client, email=customer.email)
        res = client.post(reverse('add_to_cart', args=[variant.product.id]), {'variant_id': variant.id, 'qty': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'

    def test_toggle_wishlist_unauth(self, client, product):
        res = client.post(reverse('toggle_wishlist', args=[product.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'

    def test_toggle_wishlist_no_variants(self, client, customer, product):
        product.variants.all().delete()
        _make_session(client, email=customer.email)
        res = client.post(reverse('toggle_wishlist', args=[product.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'

    def test_update_cart_ajax_coupon(self, client, customer, variant, coupon):
        from myapp.models import Cart
        cart_item = Cart.objects.create(customer=customer, variant=variant, quantity=5)
        _make_session(client, email=customer.email, coupon_id=coupon.id)
        # decrease
        res = client.get(reverse('update_cart', args=[cart_item.id, 'decrease']), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'success'
        # coupon invalid
        coupon.active = False
        coupon.save()
        res = client.get(reverse('update_cart', args=[cart_item.id, 'increase']), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'success'
        assert not res.json()['coupon_applied']
        
    def test_update_cart_ajax_stock_err(self, client, customer, variant):
        from myapp.models import Cart
        variant.stock_quantity = 1
        variant.save()
        cart_item = Cart.objects.create(customer=customer, variant=variant, quantity=1)
        _make_session(client, email=customer.email)
        res = client.get(reverse('update_cart', args=[cart_item.id, 'increase']), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'error'
        
    def test_update_cart_zero_qty(self, client, customer, variant):
        from myapp.models import Cart
        cart_item = Cart.objects.create(customer=customer, variant=variant, quantity=1)
        _make_session(client, email=customer.email)
        res = client.get(reverse('update_cart', args=[cart_item.id, 'decrease']), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json()['status'] == 'success'
        
    def test_forgot_pw_and_login_get(self, client):
        assert client.get(reverse('forgot_password')).status_code == 200
        assert client.get(reverse('login')).status_code == 200

    def test_get_product_rating_guest_session(self, client, product):
        client.get('/') # init session
        session_key = client.session.session_key
        from myapp.models import ProductReview
        ProductReview.objects.create(product=product, session_key=session_key, rating=5, review_text="x", ip_address="127.0.0.1")
        res = client.get(reverse('get_rating', args=[product.id]))
        assert res.json()['already_voted'] is True
        
    def test_submit_product_rating_missing_text(self, client, customer, product):
        _make_session(client, email=customer.email)
        res = client.post(reverse('submit_rating', args=[product.id]), json.dumps({'rating': 3, 'review_text': ''}), content_type='application/json')
        assert res.json()['status'] == 'error'
        assert res.json()['message'] == 'Review comment is mandatory.'
        
    def test_submit_product_rating_not_post(self, client, product):
        res = client.get(reverse('submit_rating', args=[product.id]))
        assert res.json()['status'] == 'error'



