import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from myapp.context_processors import cart_data, wishlist_data
from myapp.models import Customer, Product, Category, Cart, Wishlist

@pytest.mark.django_db
class TestContextProcessors:
    def test_cart_data_no_session(self):
        factory = RequestFactory()
        request = factory.get('/')
        # No session middleware run, so request.session doesn't exist?
        # Actually context processors expect a request with session.
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        
        data = cart_data(request)
        assert data['global_cart_count'] == 0
        assert data['global_cart_total'] == 0

    def test_cart_data_with_customer(self, customer, variant):
        factory = RequestFactory()
        request = factory.get('/')
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session['email'] = customer.email
        
        # Add item to cart
        variant.price = 1000
        variant.save()
        Cart.objects.create(customer=customer, variant=variant, quantity=2)
        
        data = cart_data(request)
        # subtotal = 2 * 1000 = 2000
        # Total depends on shipping logic in context_processor
        assert data['global_cart_count'] == 2
        # Check if total calculation matches expected logic (usually subtotal + shipping)
        assert data['global_cart_total'] > 0

    def test_cart_data_customer_not_found(self):
        factory = RequestFactory()
        request = factory.get('/')
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session['email'] = 'nonexistent@example.com'
        
        data = cart_data(request)
        assert data['global_cart_count'] == 0
        assert data['global_cart_total'] == 0

    def test_wishlist_data_with_customer(self, customer, variant):
        factory = RequestFactory()
        request = factory.get('/')
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session['email'] = customer.email
        
        Wishlist.objects.create(customer=customer, variant=variant)
        
        data = wishlist_data(request)
        assert variant.id in data['wishlist_ids']

    def test_wishlist_data_no_session(self):
        factory = RequestFactory()
        request = factory.get('/')
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        
        data = wishlist_data(request)
        assert data['wishlist_ids'] == []
