import pytest
from django.db import IntegrityError
from decimal import Decimal
from unittest.mock import patch
from myapp.models import Category, Brand, Product, ProductVariant, Customer, Cart, Order, OrderItem, Wishlist, ProductReview

@pytest.mark.django_db
class TestModels:
    def test_category_str(self, category):
        assert str(category) == category.name

    def test_brand_str(self, brand):
        assert str(brand) == brand.name

    def test_product_str(self, product):
        assert str(product) == product.full_name

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

    def test_wishlist_uniqueness(self, customer, variant):
        Wishlist.objects.create(customer=customer, variant=variant)
        with pytest.raises(IntegrityError):
            Wishlist.objects.create(customer=customer, variant=variant)

    def test_cart_total_price(self, customer, variant):
        cart_item = Cart.objects.create(customer=customer, variant=variant, quantity=3)
        assert cart_item.total_price() == 3 * variant.price

    def test_order_subtotal(self, order):
        order.total_amount = 1200
        order.shipping_charge = 150
        assert order.subtotal() == 1050

    def test_product_properties_and_images(self, product, variant):
        product.refresh_from_db()
        assert product.min_price == variant.price
        # image_url when no image
        assert product.featured_image_url == ""
        assert len(product.all_images) == 0

    def test_variant_attribute_str(self, variant, attribute_value):
        from myapp.models import VariantAttribute
        va = VariantAttribute.objects.create(variant=variant, attribute_value=attribute_value)
        assert str(va) == f"{variant.sku} - {attribute_value}"

    def test_order_item_line_total(self, order, variant):
        item = OrderItem.objects.create(
            order=order, variant=variant, quantity=2, snapshot_price=Decimal('100.00'), snapshot_product_name="Test"
        )
        assert item.line_total() == Decimal('200.00')

    def test_product_image_url_safe(self, product):
        from myapp.models import ProductImage
        pi = ProductImage.objects.create(product=product, image="")
        # Accessing .url on empty ImageField raises ValueError
        assert pi.image_url == ""

    def test_variant_delete_signal(self, product, variant, customer):
        from myapp.models import Attribute, AttributeValue, ProductImage
        attr = Attribute.objects.create(name="Color")
        av = AttributeValue.objects.create(attribute=attr, value="UniqueColor")
        variant.attributes.add(av)
        
        pi = ProductImage.objects.create(product=product, image="test.jpg", attribute_value=av)
        
        # Deleting the variant should trigger the signal
        variant.delete()
        assert not ProductImage.objects.filter(id=pi.id).exists()

    def test_product_complex_properties(self, product, category, attribute_value):
        from myapp.models import ProductImage, ProductVariant, VariantAttribute
        # Add image
        pi = ProductImage.objects.create(product=product, image="test.jpg", display_order=0)
        assert product.featured_image_url == pi.image.url
        assert len(product.all_images) == 1
        assert product.all_images[0]['url'] == pi.image.url

        # get_option_types
        variant = ProductVariant.objects.create(product=product, sku="VMTX", price=100)
        VariantAttribute.objects.create(variant=variant, attribute_value=attribute_value)
        options = product.get_option_types()
        assert len(options) > 0
        assert options[0]['name'] == attribute_value.attribute.name

        # get_variant_matrix
        matrix = product.get_variant_matrix()
        key = str(attribute_value.id)
        assert key in matrix
        assert matrix[key]['sku'] == "VMTX"

        # get_color_image_map
        pi_color = ProductImage.objects.create(product=product, image="color.jpg", attribute_value=attribute_value)
        color_map = product.get_color_image_map()
        assert str(attribute_value.id) in color_map
        assert pi_color.image.url in color_map[str(attribute_value.id)]

    def test_coupon_logic(self, customer):
        from myapp.models import Coupon
        from django.utils import timezone
        import datetime
        now = timezone.now()
        
        # Percentage coupon
        coupon = Coupon.objects.create(
            code="PERC10", discount_type="percentage", value=10, 
            active=True, valid_from=now - datetime.timedelta(days=1), 
            valid_to=now + datetime.timedelta(days=1)
        )
        assert coupon.is_active_now
        assert coupon.calculate_discount(1000) == Decimal('100.00')
        
        # Validation cases
        # 1. Inactive
        coupon.active = False
        valid, msg = coupon.is_valid(1000)
        assert not valid
        assert "no longer active" in msg
        coupon.active = True
        
        # 2. Expired
        coupon.valid_to = now - datetime.timedelta(days=1)
        valid, msg = coupon.is_valid(1000)
        assert not valid
        assert "expired" in msg
        coupon.valid_to = now + datetime.timedelta(days=1)

        # 3. Usage limit
        coupon.usage_limit = 5
        coupon.used_count = 5
        valid, msg = coupon.is_valid(1000)
        assert not valid
        assert "usage limit" in msg
        assert coupon.usage_percentage == 100.0
        
        # Unlimited usage percentage
        coupon.used_count = 5
        coupon.usage_limit = None # unlimited
        assert coupon.usage_percentage == 100 # because used_count > 0
        coupon.used_count = 0
        assert coupon.usage_percentage == 0
        
        # 4. Already used
        coupon.used_by_customers.add(customer)
        valid, msg = coupon.is_valid(Decimal('1000.00'), customer=customer)
        assert not valid
        assert "already used" in msg

        # 5. Success
        coupon.used_by_customers.clear()
        valid, msg = coupon.is_valid(Decimal('1000.00'))
        assert valid

        # 6. Min purchase amount
        coupon.min_purchase_amount = Decimal('500.00')
        valid, msg = coupon.is_valid(Decimal('100.00'))
        assert not valid
        assert "Spend at least" in msg

        # Discount capping
        fixed_coupon = Coupon.objects.create(
            code="FIXED100", discount_type="fixed", value=Decimal('100.00'),
            active=True, valid_from=now, valid_to=now + datetime.timedelta(days=1)
        )
        assert fixed_coupon.calculate_discount(Decimal('1000.00')) == Decimal('100.00')
        assert fixed_coupon.calculate_discount(Decimal('50.00')) == Decimal('50.00') # capped

    def test_more_model_properties(self, product, variant, order):
        # Product.total_stock
        variant.stock_quantity = 25
        variant.save()
        assert product.total_stock == 25
        
        # Order.final_total_display
        order.total_amount = 500
        assert order.final_total_display == 500
        
        # ProductVariant.in_stock
        variant.stock_quantity = 0
        assert not variant.in_stock
        variant.stock_quantity = 5
        assert variant.in_stock

    def test_variant_image_url_scoped(self, product, variant, attribute_value):
        from myapp.models import ProductImage
        # 1. Color-scoped image
        pi = ProductImage.objects.create(product=product, image="scoped.jpg", attribute_value=attribute_value)
        variant.attributes.add(attribute_value)
        assert variant.variant_image_url == pi.image.url
        assert variant.attribute_summary == str(attribute_value)
        
        # 2. Fallback to product featured image
        variant.attributes.clear()
        # We need to make sure product has a featured image but NO variant attributes match
        # Already have pi (general since its scoped but variant has none now)
        # Wait, if variant has no attributes, variant_image_url falls back to product.featured_image_url
        assert variant.variant_image_url == product.featured_image_url

    def test_image_delete_signal_file_handling(self, product):
        from myapp.models import ProductImage
        from unittest.mock import patch
        pi = ProductImage.objects.create(product=product, image="to_delete.jpg")
        
        with patch('os.path.isfile', return_value=True), \
             patch('os.remove') as mock_remove:
            pi.delete()
            # The signal should call os.remove
            assert mock_remove.called

    def test_variant_delete_signal_exception_handling(self, variant):
        from unittest.mock import patch
        # Patching inside the try block of the signal to hit line 532
        with patch('myapp.models.ProductImage.objects.filter', side_effect=Exception("Simulated Error")):
            variant.delete()
        
        # Ensure variant is gone
        assert not ProductVariant.objects.filter(id=variant.id).exists()

    def test_variant_delete_signal_shared_attribute(self, product, variant):
        from myapp.models import Attribute, AttributeValue, ProductImage, ProductVariant
        attr = Attribute.objects.create(name="Color")
        av = AttributeValue.objects.create(attribute=attr, value="SharedColor")
        
        # Two variants share the same attribute value
        variant.attributes.add(av)
        v2 = ProductVariant.objects.create(product=product, sku="V2", price=200)
        v2.attributes.add(av)
        
        pi = ProductImage.objects.create(product=product, image="shared.jpg", attribute_value=av)
        
        # Deleting the first variant should NOT delete the image because v2 still uses av
        variant.delete()
        assert ProductImage.objects.filter(id=pi.id).exists()
        
        # Deleting the last variant (v2) SHOULD delete the image
        v2.delete()
        assert not ProductImage.objects.filter(id=pi.id).exists()
