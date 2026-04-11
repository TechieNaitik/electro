import pytest
import sys
import tempfile
import shutil
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.models import User
from myapp.models import Category, Brand, Product, Customer, Cart, Order, OrderItem, Wishlist, ProductReview
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

class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    category_id = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)
    model_name = factory.Faker('word')
    variant_specs = "8GB RAM, 256GB SSD"
    sku = factory.Sequence(lambda n: f'SKU-{n}')
    description = factory.Faker('paragraph')
    price = factory.Iterator([100, 200, 500, 1000])
    stock_quantity = 50
    image = factory.django.ImageField(filename='test.jpg', width=100, height=100, color='blue')


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
def product(category, brand):
    return ProductFactory(category_id=category, brand=brand)

@pytest.fixture
def customer():
    return CustomerFactory()

@pytest.fixture
def order(customer):
    return OrderFactory(customer=customer)
