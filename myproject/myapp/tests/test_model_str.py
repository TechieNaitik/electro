import pytest
from myapp.models import (
    Customer, Category, Brand, Product, ProductImage, 
    Attribute, AttributeValue, ProductVariant, VariantAttribute,
    Order, OrderItem, Coupon
)

@pytest.mark.django_db
class TestModelStrings:
    def test_str_methods(self, category, brand, product, variant, customer):
        # Category
        assert str(category) == category.name
        
        # Brand
        assert str(brand) == brand.name
        
        # Product
        assert product.full_name in str(product)
        
        # Attribute
        attr = Attribute.objects.create(name="Color")
        assert str(attr) == "Color"
        
        # AttributeValue
        av = AttributeValue.objects.create(attribute=attr, value="Red")
        assert str(av) == "Color: Red"
        
        # ProductVariant
        v = ProductVariant(product=product, sku="SKU123")
        assert "SKU123" in str(v)
        
        # VariantAttribute
        va = VariantAttribute(variant=v, attribute_value=av)
        assert "SKU123" in str(va)
        
        # ProductImage
        pi = ProductImage.objects.create(product=product, image="test.jpg")
        assert "General" in str(pi)
        
        pi2 = ProductImage.objects.create(product=product, image="test2.jpg", attribute_value=av)
        assert "Red" in str(pi2)
        
        # SiteAdmin
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="admin_test", password="p")
        from myapp.models import SiteAdmin
        sa = SiteAdmin.objects.create(user=user)
        assert str(sa) == "admin_test"

        # Coupon
        assert str(Coupon(code="TEST")) == "TEST"
