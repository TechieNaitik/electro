import pytest
from django.db import IntegrityError
from myapp.models import Category, Brand, Product, Customer, Cart, Order, OrderItem, Wishlist, ProductReview

@pytest.mark.django_db
class TestModels:
    def test_category_str(self, category):
        assert str(category) == category.name

    def test_brand_str(self, brand):
        assert str(brand) == brand.name

    def test_product_str(self, product):
        assert str(product) == f"{product.brand.name} {product.model_name} {product.variant_specs}"

    def test_customer_str(self, customer):
        assert str(customer) == f"{customer.full_name} <{customer.email}>"

    def test_product_rating_no_reviews(self, product):
        assert product.rating == 0.0
        assert product.rounded_rating == 0.0
        assert product.total_votes == 0

    def test_product_rating_multiple_reviews(self, product, customer):
        ProductReview.objects.create(
            product=product,
            customer=customer,
            name="Naitik",
            email="naitik@example.com",
            rating=4,
            review_text="Great product!",
            ip_address="127.0.0.1"
        )
        ProductReview.objects.create(
            product=product,
            customer=customer,
            name="John",
            email="john@example.com",
            rating=5,
            review_text="Excellent!",
            ip_address="192.168.1.1"
        )
        assert product.rating == 4.5
        assert product.rounded_rating == 4.5
        assert product.total_votes == 2

    def test_wishlist_uniqueness(self, customer, product):
        Wishlist.objects.create(customer=customer, product=product)
        with pytest.raises(IntegrityError):
            Wishlist.objects.create(customer=customer, product=product)

    def test_cart_total_price(self, customer, product):
        cart_item = Cart.objects.create(customer=customer, product=product, quantity=3)
        assert cart_item.total_price() == 3 * product.price

    def test_order_subtotal(self, order):
        order.total_amount = 1200
        order.shipping_charge = 150
        assert order.subtotal() == 1050
