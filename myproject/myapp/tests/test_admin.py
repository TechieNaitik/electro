import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import admin as django_admin
from myapp.models import (
    Customer, Product, Category, Brand, Order, OrderItem, ProductVariant, 
    Coupon, SiteAdmin
)
from io import BytesIO

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username='admin', password='password123')
    SiteAdmin.objects.create(user=user)
    return user

@pytest.fixture
def admin_client(client, admin_user):
    # Mimic the custom session login
    session = client.session
    session['_site_admin_user_id'] = admin_user.id
    session.save()
    return client

@pytest.mark.django_db
class TestAdminViews:
    
    def test_admin_dashboard(self, admin_client):
        response = admin_client.get(reverse('custom_admin:dashboard'))
        assert response.status_code == 200
        assert 'custom_admin/dashboard.html' in [t.name for t in response.templates]

    def test_admin_brands_crud(self, admin_client):
        # Add
        response = admin_client.post(reverse('custom_admin:brand_add'), {'name': 'New Brand'})
        assert response.status_code == 302
        assert Brand.objects.filter(name='New Brand').exists()
        brand = Brand.objects.get(name='New Brand')
        
        # Edit
        response = admin_client.post(reverse('custom_admin:brand_edit', args=[brand.id]), {'name': 'Updated Brand'})
        assert response.status_code == 302
        brand.refresh_from_db()
        assert brand.name == 'Updated Brand'
        
        # List
        response = admin_client.get(reverse('custom_admin:brands'))
        assert response.status_code == 200
        
        # Delete
        response = admin_client.post(reverse('custom_admin:brand_delete', args=[brand.id]))
        assert response.status_code == 302
        assert not Brand.objects.filter(id=brand.id).exists()

    def test_admin_categories_crud(self, admin_client):
        # Add
        response = admin_client.post(reverse('custom_admin:category_add'), {'name': 'New Cat'})
        assert response.status_code == 302
        assert Category.objects.filter(name='New Cat').exists()
        cat = Category.objects.get(name='New Cat')
        
        # Edit
        response = admin_client.post(reverse('custom_admin:category_edit', args=[cat.id]), {'name': 'Updated Cat'})
        assert response.status_code == 302
        cat.refresh_from_db()
        assert cat.name == 'Updated Cat'
        
        # Delete
        response = admin_client.post(reverse('custom_admin:category_delete', args=[cat.id]))
        assert response.status_code == 302
        assert not Category.objects.filter(id=cat.id).exists()

    def test_admin_customers_list(self, admin_client, customer):
        response = admin_client.get(reverse('custom_admin:customers'))
        assert response.status_code == 200
        assert customer.full_name in response.content.decode()

    def test_admin_orders_list(self, admin_client, order):
        response = admin_client.get(reverse('custom_admin:orders'))
        assert response.status_code == 200
        assert str(order.id) in response.content.decode()

    def test_admin_analytical_dashboard_apis(self, admin_client, category, brand, product, variant, customer):
        # Create some data for analytics
        order = Order.objects.create(customer=customer, total_amount=100)
        from myapp.models import OrderItem # Import inside or at top
        OrderItem.objects.create(order=order, variant=variant, quantity=1, snapshot_price=100, snapshot_product_name="P")
        
        # Test Dashboard Stats API - No filters
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'))
        assert response.status_code == 200
        assert 'kpis' in response.json()

        # Test with category filter
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'category': category.id})
        assert response.status_code == 200

        # Test with brand filter
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'brand': brand.id})
        assert response.status_code == 200

        # Test with custom date range
        import datetime
        today = datetime.date.today()
        start = today - datetime.timedelta(days=7)
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {
            'range': 'custom',
            'start_date': start.strftime('%Y-%m-%d')
        })
        assert response.status_code == 200

        # Test with flatpickr range format "YYYY-MM-DD to YYYY-MM-DD"
        range_str = f"{start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': range_str})
        assert response.status_code == 200

    def test_admin_analytical_dashboard_apis_edge_cases(self, admin_client):
        from django.core.cache import cache
        cache.clear() # Clear cache to ensure logic is hit

        # 1. Test Range 'today'
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': 'today'})
        assert response.status_code == 200

        # 2. Test Range '7d'
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': '7d'})
        assert response.status_code == 200

        # 3. Test Cache Hit
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': '30d'})
        cache_key = [k for k in cache._cache.keys() if 'dashboard_stats' in k] # Depends on cache backend, but we just need it to be in there
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': '30d'})
        assert response.status_code == 200

        # 4. Test Invalid Custom Date
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {
            'range': 'custom',
            'start_date': 'invalid-date'
        })
        assert response.status_code == 200

        # 5. Test Invalid Flatpickr Range
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': 'not_a_range to invalid'})
        assert response.status_code == 200

    def test_admin_unauthorized_api(self, client):
        # We use 'client' here without admin_client fixture to ensure no session is set
        response = client.get(reverse('custom_admin:api_dashboard_stats'))
        assert response.status_code == 401
        assert response.json()['error'] == 'Unauthorized'

    def test_product_properties(self, product, variant):
        # min_price
        variant.price = 50
        variant.is_active = True
        variant.save()
        assert product.min_price == 50
        
        # total_stock
        variant.stock_quantity = 10
        variant.save()
        assert product.total_stock == 10
        
        # featured_image_url
        assert product.featured_image_url == "" # No image

    def test_order_properties(self, order, variant):
        from myapp.models import OrderItem
        OrderItem.objects.create(order=order, variant=variant, quantity=2, snapshot_price=100, snapshot_product_name="P")
        # Order doesn't have total_items property, but it has subtotal()
        assert order.subtotal() >= 0
        assert order.final_total_display == order.total_amount

    def test_admin_custom_methods(self):
        from myapp.admin import CouponAdmin, ProductVariantAdmin, ProductImageInline, ProductVariantInlineForProduct
        from myapp.models import Coupon, ProductVariant, ProductImage
        from django.contrib import admin as django_admin
        
        # Coupon usage_percentage
        coupon_admin = CouponAdmin(Coupon, django_admin.site)
        c1 = Coupon(usage_limit=100, used_count=50)
        assert "50.0%" in str(coupon_admin.usage_percentage(c1))
        
        c2 = Coupon(usage_limit=0, used_count=5)
        assert "Unlimited" == coupon_admin.usage_percentage(c2)
        
        # Variant list methods
        variant_admin = ProductVariantAdmin(ProductVariant, django_admin.site)
        v = ProductVariant(price=500)
        assert variant_admin.price(v) == 500

        # Inlines and Badges
        inline = ProductVariantInlineForProduct(ProductVariant, django_admin.site)
        v.pk = 1
        v.stock_quantity = 10
        assert "In Stock" in str(inline.stock_badge(v))
        v.stock_quantity = 0
        assert "Out of Stock" in str(inline.stock_badge(v))

        # Image Preview
        img_inline = ProductImageInline(ProductImage, django_admin.site)
        pi = ProductImage()
        assert img_inline.image_preview(pi) == "—"
        
        # Test valid image preview
        from django.core.files.uploadedfile import SimpleUploadedFile
        pi.pk = 1
        pi.image = SimpleUploadedFile("test.jpg", b"content")
        assert 'src="' in str(img_inline.image_preview(pi))

    def test_admin_actions(self, admin_client, product, variant, customer):
        from myapp.models import Coupon, ProductVariant
        from myapp.admin import CouponAdmin, ProductVariantAdmin
        from django.contrib import admin as django_admin
        
        # 1. Coupon Export Action
        from django.utils import timezone
        now = timezone.now()
        coupon = Coupon.objects.create(
            code="EXPORTME", discount_type="PERCENTAGE", value=10, active=True,
            valid_from=now, valid_to=now + timezone.timedelta(days=1)
        )
        coupon_admin = CouponAdmin(Coupon, django_admin.site)
        response = coupon_admin.export_usage_report(None, Coupon.objects.filter(id=coupon.id))
        assert response.status_code == 200
        assert response['Content-Disposition'] == 'attachment; filename="coupon_usage_report.csv"'

        # 2. Bulk Actions for Variants
        v1 = ProductVariant.objects.create(product=product, sku="V1", price=100, stock_quantity=10, is_active=False)
        v2 = ProductVariant.objects.create(product=product, sku="V2", price=100, stock_quantity=10, is_active=True)
        
        variant_admin = ProductVariantAdmin(ProductVariant, django_admin.site)
        # Mock request for message_user
        from unittest.mock import MagicMock
        request = MagicMock()
        
        variant_admin.bulk_mark_active(request, ProductVariant.objects.filter(id=v1.id))
        v1.refresh_from_db()
        assert v1.is_active is True
        
        variant_admin.bulk_mark_inactive(request, ProductVariant.objects.filter(id=v2.id))
        v2.refresh_from_db()
        assert v2.is_active is False

    def test_admin_coupons_crud(self, admin_client):
        # Add
        from django.utils import timezone
        import datetime
        data = {
            'code': 'ADMIN10',
            'discount_type': 'percentage',
            'value': 10,
            'valid_from': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'valid_to': (timezone.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'active': True,
            'min_purchase_amount': 0
        }
        admin_client.post(reverse('custom_admin:coupon_add'), data)
        assert Coupon.objects.filter(code='ADMIN10').exists()
        coupon = Coupon.objects.get(code='ADMIN10')

        # Edit
        data['value'] = 20
        admin_client.post(reverse('custom_admin:coupon_edit', args=[coupon.id]), data)
        coupon.refresh_from_db()
        assert coupon.value == 20

        # Delete
        admin_client.post(reverse('custom_admin:coupon_delete', args=[coupon.id]))
        assert not Coupon.objects.filter(id=coupon.id).exists()

    def test_admin_export_customers_csv(self, admin_client, customer):
        response = admin_client.get(reverse('custom_admin:export'), {
            'module': 'customers',
            'format': 'csv'
        })
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']
        assert customer.email in response.content.decode()

    def test_admin_login_page(self, client):
        response = client.get(reverse('custom_admin:login'))
        assert response.status_code == 200
        assert 'custom_admin/login.html' in [t.name for t in response.templates]

    def test_admin_logout(self, admin_client):
        response = admin_client.get(reverse('custom_admin:logout'))
        assert response.status_code == 302
        assert response.url == reverse('custom_admin:login')
        assert '_site_admin_user_id' not in admin_client.session

    def test_site_admin_logic(self, db):
        from myapp.admin import SiteAdminForm, SiteAdminAdmin
        from myapp.models import SiteAdmin
        from django.contrib.auth.models import User
        import unittest.mock as mock
        
        # 1. SiteAdminForm Init for Existing Instance
        user = User.objects.create_user(username='sa', email='sa@ex.com')
        sa = SiteAdmin.objects.create(user=user)
        form = SiteAdminForm(instance=sa)
        assert form.fields['username'].initial == 'sa'
        
        # 2. SiteAdminForm Clean duplicate username
        form_data = {'username': 'sa', 'email': 'sa@ex.com', 'password': 'p'}
        form = SiteAdminForm(data=form_data)
        assert not form.is_valid()
        assert 'A user with this username already exists' in str(form.errors)

        # 3. Save model overrides (Creation)
        admin_site = mock.MagicMock()
        sa_admin = SiteAdminAdmin(SiteAdmin, admin_site)
        request = mock.MagicMock()
        request.user = user
        
        new_sa = SiteAdmin()
        form = SiteAdminForm(data={'username': 'newsa', 'email': 'new@ex.com', 'password': 'p'})
        assert form.is_valid()
        sa_admin.save_model(request, new_sa, form, change=False)
        assert User.objects.filter(username='newsa').exists()
        
        # 4. Save model overrides (Update)
        form = SiteAdminForm(data={'username': 'sa_edit', 'email': 'sa_edit@ex.com', 'password': 'p2'})
        assert form.is_valid()
        sa_admin.save_model(request, sa, form, change=True)
        user.refresh_from_db()
        assert user.username == 'sa_edit'

    def test_admin_save_delete_logging(self, db):
        from myapp.admin import CategoryAdmin, BrandAdmin, ProductAdmin, ProductVariantInlineForProduct
        from myapp.models import Category, Brand, Product, ProductVariant
        from unittest.mock import MagicMock, patch
        from django.contrib import admin as django_admin
        
        request = MagicMock()
        request.user.username = "testadmin"
        
        # Create locally
        category = Category.objects.create(name="C1")
        brand = Brand.objects.create(name="B1")
        product = Product.objects.create(model_name="P1", category_id=category, brand=brand)
        
        # We patch the base class methods to reach our custom logic without DB errors
        with patch('django.contrib.admin.ModelAdmin.save_model'), \
             patch('django.contrib.admin.ModelAdmin.delete_model'):
             
            # Category
            cat_admin = CategoryAdmin(Category, django_admin.site)
            cat_admin.save_model(request, category, None, change=False)
            cat_admin.save_model(request, category, None, change=True)
            cat_admin.delete_model(request, category)
            
            # Brand
            brand_admin = BrandAdmin(Brand, django_admin.site)
            brand_admin.save_model(request, brand, None, change=False)
            brand_admin.save_model(request, brand, None, change=True)
            brand_admin.delete_model(request, brand)
            
            # Product
            prod_admin = ProductAdmin(Product, django_admin.site)
            prod_admin.min_price_display(product)
            prod_admin.total_stock_display(product)
            prod_admin.save_model(request, product, MagicMock(), change=False)
            prod_admin.save_model(request, product, MagicMock(), change=True)
            prod_admin.delete_model(request, product)
        
        # Variant Stock Badge '—' branch
        variant_inline = ProductVariantInlineForProduct(ProductVariant, django_admin.site)
        v_new = ProductVariant()
        assert variant_inline.stock_badge(v_new) == "—"

    def test_coupon_admin_colors(self):
        from myapp.admin import CouponAdmin
        from myapp.models import Coupon
        ca = CouponAdmin(Coupon, django_admin.site)
        
        c = Coupon(usage_limit=10, used_count=9) # 90% -> orange
        assert 'color: orange' in ca.usage_percentage(c)
        
        c.used_count = 10 # 100% -> red
        assert 'color: red' in ca.usage_percentage(c)
        
        c.usage_limit = None # Unlimited
        assert ca.usage_percentage(c) == "Unlimited"

    def test_attribute_image_preview(self, db):
        from myapp.admin import AttributeImageInline
        from myapp.models import ProductImage
        from django.core.files.uploadedfile import SimpleUploadedFile
        inline = AttributeImageInline(ProductImage, django_admin.site)
        pi = ProductImage()
        assert inline.image_preview(pi) == "—"
        
        pi.pk = 1
        pi.image = SimpleUploadedFile("attr.jpg", b"content")
        assert 'src="' in str(inline.image_preview(pi))
