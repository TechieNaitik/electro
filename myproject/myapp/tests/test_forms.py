import pytest
from myapp.forms import CategoryForm, BrandForm, ProductForm
from django import forms
from myapp.models import Category, Brand

from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.fixture
def dummy_image():
    # A tiny 1x1 transparent pixel gif
    return SimpleUploadedFile(
        "test.gif", b"GIF89a\x01\x00\x01\x00\x00\x00\x00;", content_type="image/gif"
    )

@pytest.mark.django_db
class TestForms:
    def test_category_form_valid(self):
        form = CategoryForm(data={'name': 'Electronics'})
        assert form.is_valid()
        
    def test_category_form_invalid(self):
        form = CategoryForm(data={'name': ''})
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_brand_form_valid(self):
        form = BrandForm(data={'name': 'Apple'})
        assert form.is_valid()

    def test_product_form_price_validation(self, category, brand, dummy_image):
        data = {
            'category_id': category.id,
            'brand': brand.id,
            'model_name': 'iPhone 15',
            'variant_specs': '128GB',
            'description': 'Description',
            'price': -100,  # Invalid price
            'stock_quantity': 50
        }
        form = ProductForm(data=data, files={'image': dummy_image})
        assert not form.is_valid()
        assert 'price' in form.errors

    def test_product_form_stock_validation(self, category, brand, dummy_image):
        data = {
            'category_id': category.id,
            'brand': brand.id,
            'model_name': 'iPhone 15',
            'variant_specs': '128GB',
            'description': 'Description',
            'price': 1000,
            'stock_quantity': -10  # Invalid stock
        }
        form = ProductForm(data=data, files={'image': dummy_image})
        assert not form.is_valid()
        assert 'stock_quantity' in form.errors

    def test_coupon_form_initial_datetime(self):
        from myapp.models import Coupon
        from django.utils import timezone
        from myapp.forms import CouponForm
        import datetime

        now = timezone.now()
        coupon = Coupon(
            code='SAVE10', 
            valid_from=now,
            valid_to=now + datetime.timedelta(days=1),
            value=10,
            discount_type='percentage'
        )
        form = CouponForm(instance=coupon)
        assert form.initial['valid_from'] == now.strftime('%Y-%m-%dT%H:%M')
        assert form.initial['valid_to'] == (now + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')

    def test_attribute_form_valid(self, category):
        from myapp.forms import AttributeForm
        data = {
            'name': 'Color',
            'category': category.id,
            'display_order': 1
        }
        form = AttributeForm(data=data)
        assert form.is_valid()

    def test_product_variant_form_valid(self, product):
        from myapp.forms import ProductVariantForm
        data = {
            'product': product.id,
            'sku': 'SKU-123',
            'price': 999.99,
            'stock_quantity': 10,
            'is_active': True
        }
        form = ProductVariantForm(data=data)
        assert form.is_valid()

    def test_product_form_clean_stock_manual(self):
        """Manually test clean_stock_quantity to hit line 68 coverage."""
        from myapp.forms import ProductForm
        form = ProductForm()
        form.cleaned_data = {'stock_quantity': -1}
        with pytest.raises(forms.ValidationError) as excinfo:
            form.clean_stock_quantity()
        assert "Stock quantity cannot be negative" in str(excinfo.value)

    def test_product_form_clean_price_manual(self):
        """Manually test clean_price to hit line 62 coverage."""
        from myapp.forms import ProductForm
        form = ProductForm()
        form.cleaned_data = {'price': -1}
        with pytest.raises(forms.ValidationError) as excinfo:
            form.clean_price()
        assert "Price cannot be negative" in str(excinfo.value)

    def test_formsets(self, product):
        from myapp.forms import ProductImageFormSet, AttributeValueFormSet
        from myapp.models import Attribute
        
        # Test ProductImageFormSet
        formset = ProductImageFormSet(instance=product)
        assert len(formset.forms) == 5

        # Test AttributeValueFormSet
        attr = Attribute.objects.create(name="Size")
        formset = AttributeValueFormSet(instance=attr)
        assert len(formset.forms) == 5

