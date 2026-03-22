import pytest
from myapp.forms import CategoryForm, BrandForm, ProductForm
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

