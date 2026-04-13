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

    def test_product_form_valid(self, category, brand):
        data = {
            'category_id': category.id,
            'brand': brand.id,
            'model_name': 'iPhone 15',
            'description': 'Description',
            'is_featured': False
        }
        form = ProductForm(data=data)
        assert form.is_valid()

    def test_product_variant_form_price_validation(self, product):
        from myapp.forms import ProductVariantForm
        data = {
            'product': product.id,
            'sku': 'SKU-NEG',
            'price': -100,  # Invalid price
            'stock_quantity': 50,
            'reorder_threshold': 10
        }
        form = ProductVariantForm(data=data)
        # DecimalField with min_value/validators or handled by DB 
        # Usually forms handle min_value if specified in widgets or field override
        # Here we just check if it's invalid assuming some validation exists or we add it
        assert "Price cannot be negative" in str(form.errors['price'])

    def test_product_variant_form_stock_validation(self, product):
        from myapp.forms import ProductVariantForm
        data = {
            'product': product.id,
            'sku': 'SKU-NEG-STOCK',
            'price': 1000,
            'stock_quantity': -10,  # Invalid stock
            'reorder_threshold': 10
        }
        form = ProductVariantForm(data=data)
        assert not form.is_valid()
        assert "greater than or equal to 0" in str(form.errors['stock_quantity'])

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
            'categories': [category.id],
            'display_order': 1
        }
        form = AttributeForm(data=data)
        assert form.is_valid()

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

    def test_variant_attribute_formset(self, product):
        from myapp.models import ProductVariant
        from myapp.forms import VariantAttributeFormSet
        variant = ProductVariant.objects.create(
            product=product,
            sku='VA-FORMSET-TEST',
            price=100,
            stock_quantity=10
        )
        formset = VariantAttributeFormSet(instance=variant)
        assert len(formset.forms) == 4

    def test_product_variant_form_stock_validation_direct(self):
        """Specifically test the clean_stock_quantity method which is unreachable via is_valid due to PositiveIntegerField."""
        from myapp.forms import ProductVariantForm
        form = ProductVariantForm()
        form.cleaned_data = {'stock_quantity': -5}
        with pytest.raises(forms.ValidationError) as excinfo:
            form.clean_stock_quantity()
        assert "Stock cannot be negative" in str(excinfo.value)
        
        # Test valid case for completeness
        form.cleaned_data = {'stock_quantity': 10}
        assert form.clean_stock_quantity() == 10

    def test_product_image_form_init(self):
        """Test ProductImageForm's initialization logic for queryset and empty label."""
        from myapp.forms import ProductImageForm
        from myapp.models import AttributeValue, Attribute
        
        # Create some attribute values
        attr = Attribute.objects.create(name="Color")
        AttributeValue.objects.create(attribute=attr, value="Red")
        AttributeValue.objects.create(attribute=attr, value="Blue")
        
        form = ProductImageForm()
        assert form.fields['attribute_value'].empty_label == "General (All Variants)"
        # Queryset should be Ordered by attribute name and value
        qs = form.fields['attribute_value'].queryset
        assert qs.count() >= 2
        assert "Color" in str(qs.first().attribute.name)

