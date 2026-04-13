import pytest
import sys
import tempfile
import shutil
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from myapp.models import (
    Category, Brand, Product, Customer, Cart, Order, OrderItem, 
    Wishlist, ProductReview, Attribute, AttributeValue, ProductVariant, Coupon
)
import factory
from faker import Factory as FakerFactory

faker = FakerFactory.create()

@pytest.fixture(autouse=True)
def use_dummy_staticfiles(settings):
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    settings.WHITENOISE_MANIFEST_STRICT = False
    # Remove WhiteNoise from middleware to avoid warnings about missing STATIC_ROOT in tests
    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if 'whitenoise' not in m.lower()]

@pytest.fixture(autouse=True)
def media_storage(settings):
    temp_media = tempfile.mkdtemp()
    settings.MEDIA_ROOT = temp_media
    yield
    shutil.rmtree(temp_media, ignore_errors=True)

@pytest.fixture(autouse=True)
def mock_background_tasks():
    with patch('threading.Thread'), patch('myapp.email_utils.send_order_email'):
        yield

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Iterator(['Electronics', 'Laptops', 'Smartphones', 'Accessories'])

class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand
    name = factory.Sequence(lambda n: f'Brand {n}')

class AttributeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attribute
    name = factory.Sequence(lambda n: f'Attribute {n}')
    display_order = factory.Sequence(lambda n: n)

class AttributeValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttributeValue
    attribute = factory.SubFactory(AttributeFactory)
    value = factory.Sequence(lambda n: f'Value {n}')
    display_order = factory.Sequence(lambda n: n)

class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    category_id = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)
    model_name = factory.Faker('word')
    description = factory.Faker('paragraph')
    is_featured = False

class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant
    product = factory.SubFactory(ProductFactory)
    sku = factory.Sequence(lambda n: f'SKU-{n}')
    price = factory.Iterator([100, 200, 500, 1000])
    stock_quantity = 50

class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer
    full_name = factory.Faker('name')
    email = factory.Sequence(lambda n: f'customer{n}@example.com')
    password = 'password123'
    phone = '1234567890'

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order
    customer = factory.SubFactory(CustomerFactory)
    total_amount = 1000
    payment_method = 'Cash on Delivery'
    status = 'Pending'

class CouponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Coupon
    code = factory.Sequence(lambda n: f'COUPON-{n}')
    discount_type = 'percentage'
    value = 10
    active = True
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = factory.LazyFunction(lambda: timezone.now() + datetime.timedelta(days=7))

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def category():
    return CategoryFactory()

@pytest.fixture
def brand():
    return BrandFactory()

@pytest.fixture
def attribute():
    return AttributeFactory()

@pytest.fixture
def attribute_value(attribute):
    return AttributeValueFactory(attribute=attribute)

@pytest.fixture
def product(category, brand):
    return ProductFactory(category_id=category, brand=brand)

@pytest.fixture
def variant(product):
    return ProductVariantFactory(product=product)

@pytest.fixture
def customer():
    return CustomerFactory()

@pytest.fixture
def order(customer):
    return OrderFactory(customer=customer)

@pytest.fixture
def coupon():
    return CouponFactory()
