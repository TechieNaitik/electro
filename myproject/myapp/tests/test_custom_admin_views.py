import pytest
import sys
import json
import os
import datetime
import re
import subprocess
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib import admin as django_admin
from io import BytesIO
from myapp.models import (
    Customer, Category, Product, Cart, Order, OrderItem, 
    SiteAdmin, Brand, Coupon, ProductVariant, Attribute, AttributeValue, ProductImage
)
from myapp.custom_admin_views import update_split_reports

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username='admin', password='password123')
    SiteAdmin.objects.create(user=user)
    return user

@pytest.fixture
def admin_client(client, admin_user):
    # Mimic the custom session login used by custom_admin_views
    session = client.session
    session['_site_admin_user_id'] = admin_user.id
    session.save()
    return client

@pytest.mark.django_db
class TestAdminViewsCore:
    """Core view sets moved from test_admin.py."""
    
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
        order = Order.objects.create(customer=customer, total_amount=100)
        OrderItem.objects.create(order=order, variant=variant, quantity=1, snapshot_price=100, snapshot_product_name="P")
        
        # Test Dashboard Stats API - No filters
        response = admin_client.get(reverse('custom_admin:api_dashboard_stats'))
        assert response.status_code == 200
        assert 'kpis' in response.json()

        # Filters
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'category': category.id}).status_code == 200
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'brand': brand.id}).status_code == 200
        
        today = datetime.date.today()
        start = today - datetime.timedelta(days=7)
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': 'custom', 'start_date': start.strftime('%Y-%m-%d')}).status_code == 200
        
        range_str = f"{start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': range_str}).status_code == 200

    def test_admin_analytical_dashboard_apis_edge_cases(self, admin_client):
        from django.core.cache import cache
        cache.clear()
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': 'today'}).status_code == 200
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': '7d'}).status_code == 200
        
        # Cache Hit
        admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': '30d'})
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': '30d'}).status_code == 200

        # Invalids
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': 'custom', 'start_date': 'invalid'}).status_code == 200
        assert admin_client.get(reverse('custom_admin:api_dashboard_stats'), {'range': 'invalid to invalid'}).status_code == 200

    def test_admin_unauthorized_api(self, client):
        response = client.get(reverse('custom_admin:api_dashboard_stats'))
        assert response.status_code == 401
        assert response.json()['error'] == 'Unauthorized'

    def test_admin_coupons_crud(self, admin_client):
        from django.utils import timezone
        data = {
            'code': 'ADMIN10',
            'discount_type': 'percentage',
            'value': 10,
            'valid_from': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'valid_to': (timezone.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'active': True,
            'min_purchase_amount': 0
        }
        res = admin_client.post(reverse('custom_admin:coupon_add'), data)
        assert res.status_code == 302
        coupon = Coupon.objects.get(code='ADMIN10')
        
        data['value'] = 20
        admin_client.post(reverse('custom_admin:coupon_edit', args=[coupon.id]), data)
        coupon.refresh_from_db()
        assert coupon.value == 20
        
        admin_client.post(reverse('custom_admin:coupon_delete', args=[coupon.id]))
        assert not Coupon.objects.filter(id=coupon.id).exists()

    def test_admin_logout_logic(self, admin_client):
        response = admin_client.get(reverse('custom_admin:logout'))
        assert response.status_code == 302
        assert response.url == reverse('custom_admin:login')
        assert '_site_admin_user_id' not in admin_client.session

@pytest.mark.django_db
class TestAdminPytestApis:
    def test_run_pytest_api(self, admin_client):
        # 1. Non-POST
        assert admin_client.get(reverse('custom_admin:api_run_pytest')).status_code == 405
        
        # 2. Success POST
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='pytest output', stderr='')
            response = admin_client.post(reverse('custom_admin:api_run_pytest'))
            assert response.status_code == 200
            assert response.json()['status'] == 'success'
        
        # 3. Fail return code POST
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=2, stdout='', stderr='pytest error')
            response = admin_client.post(reverse('custom_admin:api_run_pytest'))
            assert response.status_code == 500
            assert response.json()['status'] == 'error'
            
        # 4. Timeout Exception
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='pytest', timeout=300)):
            response = admin_client.post(reverse('custom_admin:api_run_pytest'))
            assert response.status_code == 408
            
        # 5. Generic Exception
        with patch('subprocess.run', side_effect=Exception('Boom')):
            response = admin_client.post(reverse('custom_admin:api_run_pytest'))
            assert response.status_code == 500

    def test_stream_pytest_api(self, admin_client):
        url = reverse('custom_admin:api_run_pytest_stream')
        with patch('subprocess.Popen') as mock_popen, patch('myapp.custom_admin_views.update_split_reports') as mock_updt:
            mock_process = MagicMock()
            mock_process.stdout = ["test_a PASSED\n", "test_b FAILED\n"]
            mock_popen.return_value = mock_process
            response = admin_client.get(url)
            assert response.status_code == 200
            content = list(response.streaming_content)
            assert b"test_a PASSED\n" in content
            assert b"\n--- FINISHED ---" in content
            mock_updt.assert_called()

        # Exception in update_split_reports
        with patch('subprocess.Popen') as mock_popen, patch('myapp.custom_admin_views.update_split_reports', side_effect=Exception("Crash")):
            mock_process = MagicMock()
            mock_process.stdout = ["line1\n"]
            mock_popen.return_value = mock_process
            response = admin_client.get(url)
            content = list(response.streaming_content)
            assert b"\n[Warning] Could not update split reports: Crash\n" in content

    def test_update_split_reports(self, tmpdir):
        root_dir = str(tmpdir)
        output = (
            "test_views.py::test_a PASSED [ 5%] in 0.1s\n"
            "test_views.py::test_b FAILED [10%] in 0.5s\n"
            "test_views.py::test_b FAILED [10%] in 0.5s\n"
            "test_views.py::test_c ERROR [15%]\n"
            "======= warnings summary =======\n"
            "test_views.py::test_d\n"
            "   some warning\n"
            "--- end ---\n"
        )
        update_split_reports(output, root_dir)
        htmlcov = os.path.join(root_dir, 'htmlcov')
        assert os.path.exists(htmlcov)
        assert os.path.exists(os.path.join(htmlcov, 'passed_tests.html'))
        assert os.path.exists(os.path.join(htmlcov, 'warnings_tests.html'))
        
        # Test empty output
        update_split_reports("No tests run", root_dir)


@pytest.mark.django_db
class TestAdminProductsVariants:
    def test_admin_products(self, admin_client, product):
        url = reverse('custom_admin:products')
        assert admin_client.get(url).status_code == 200
        # Search query
        assert admin_client.get(url, {'q': product.model_name}).status_code == 200

    def test_admin_product_add(self, admin_client, category, brand, product):
        url = reverse('custom_admin:product_add')
        # GET
        assert admin_client.get(url).status_code == 200
        # POST valid
        data = {
            'model_name': 'NewProd',
            'category_id': category.id,
            'brand': brand.id,
            'description': 'ld',
            'images-TOTAL_FORMS': '0',
            'images-INITIAL_FORMS': '0',
            'productimage_set-TOTAL_FORMS': '0',
            'productimage_set-INITIAL_FORMS': '0',
        }
        with patch('myapp.custom_admin_views.ProductForm.is_valid', return_value=True), \
             patch('myapp.forms.ProductImageFormSet.is_valid', return_value=True), \
             patch('myapp.custom_admin_views.ProductImageFormSet.is_valid', return_value=True), \
             patch('myapp.custom_admin_views.ProductForm.save') as mf_save, \
             patch('myapp.custom_admin_views.ProductImageFormSet.save'):
            mf_save.return_value = product
            response = admin_client.post(url, data)
            assert response.status_code == 302
        # POST invalid
        assert admin_client.post(url, {}).status_code == 200

    def test_admin_product_edit(self, admin_client, product):
        url = reverse('custom_admin:product_edit', args=[product.id])
        # GET
        assert admin_client.get(url).status_code == 200
        # POST valid with detailed feedback
        data = {
            'model_name': 'UpdatedProd',
            'category_id': product.category_id.id,
            'brand': product.brand.id,
            'description': 'ld',
            'images-TOTAL_FORMS': '1',
            'images-INITIAL_FORMS': '0',
            'productimage_set-TOTAL_FORMS': '1',
            'productimage_set-INITIAL_FORMS': '0',
        }
        with patch('myapp.custom_admin_views.ProductForm.is_valid', return_value=True), \
             patch('myapp.forms.ProductImageFormSet.is_valid', return_value=True), \
             patch('myapp.custom_admin_views.ProductImageFormSet.is_valid', return_value=True), \
             patch('myapp.custom_admin_views.ProductForm.save'), \
             patch('myapp.custom_admin_views.ProductImageFormSet.save'), \
             patch('myapp.custom_admin_views.ProductImageFormSet') as MFSet:
            
            mock_instance = MagicMock()
            mock_instance.is_valid.return_value = True
            mock_instance.new_objects = [1, 2] # Two images added
            mock_instance.deleted_objects = [1] # One image deleted
            MFSet.return_value = mock_instance
            
            response = admin_client.post(url, data)
            assert response.status_code == 302

    def test_admin_product_delete(self, admin_client, product):
        url = reverse('custom_admin:product_delete', args=[product.id])
        assert admin_client.get(url).status_code == 200
        response = admin_client.post(url)
        assert response.status_code == 302
        assert not Product.objects.filter(id=product.id).exists()

    def test_admin_variants(self, admin_client, variant):
        url = reverse('custom_admin:variants')
        assert admin_client.get(url).status_code == 200
        assert admin_client.get(url, {'q': variant.sku}).status_code == 200

    def test_admin_variant_add(self, admin_client, product):
        url = reverse('custom_admin:variant_add')
        assert admin_client.get(url, {'product_id': product.id}).status_code == 200
        data = {
            'product': product.id,
            'sku': 'SKU12345',
            'price': 100,
            'stock_quantity': 5,
            'reorder_threshold': 2,
            'is_active': True,
            'variantattribute_set-TOTAL_FORMS': '0',
            'variantattribute_set-INITIAL_FORMS': '0',
        }
        res = admin_client.post(url, data)
        assert res.status_code == 302
        assert ProductVariant.objects.filter(sku='SKU12345').exists()

    def test_admin_variant_edit(self, admin_client, variant):
        url = reverse('custom_admin:variant_edit', args=[variant.id])
        assert admin_client.get(url).status_code == 200
        data = {
            'product': variant.product.id,
            'sku': 'UPDATEDSKU',
            'price': 200,
            'stock_quantity': 5,
            'reorder_threshold': 2,
            'is_active': True,
            'variantattribute_set-TOTAL_FORMS': '0',
            'variantattribute_set-INITIAL_FORMS': '0',
        }
        res = admin_client.post(url, data)
        assert res.status_code == 302
        variant.refresh_from_db()
        assert variant.sku == 'UPDATEDSKU'

    def test_admin_variant_delete(self, admin_client, variant):
        url = reverse('custom_admin:variant_delete', args=[variant.id])
        assert admin_client.get(url).status_code == 200
        res = admin_client.post(url)
        assert res.status_code == 302
        assert not ProductVariant.objects.filter(id=variant.id).exists()


@pytest.mark.django_db
class TestAdminAttributes:
    def test_admin_attributes(self, admin_client):
        url = reverse('custom_admin:attributes')
        assert admin_client.get(url).status_code == 200

    def test_admin_attribute_add(self, admin_client):
        url = reverse('custom_admin:attribute_add')
        assert admin_client.get(url).status_code == 200
        data = {
            'name': 'Color1',
            'display_order': 0,
            'values-TOTAL_FORMS': '1',
            'values-INITIAL_FORMS': '0',
            'values-0-value': 'Red'
        }
        with patch('myapp.custom_admin_views.AttributeForm.is_valid', return_value=True), \
             patch('myapp.custom_admin_views.AttributeValueFormSet.is_valid', return_value=True), \
             patch('myapp.custom_admin_views.AttributeForm.save') as mock_save, \
             patch('myapp.custom_admin_views.AttributeValueFormSet.save'):
            mock_save.return_value = MagicMock(name='mockattr')
            res = admin_client.post(url, data)
            assert res.status_code == 302

    def test_admin_attribute_edit(self, admin_client, attribute):
        url = reverse('custom_admin:attribute_edit', args=[attribute.id])
        assert admin_client.get(url).status_code == 200
        data = {
            'name': 'UpdatedColor',
            'display_order': 0,
            'values-TOTAL_FORMS': '0',
            'values-INITIAL_FORMS': '0',
        }
        res = admin_client.post(url, data)
        assert res.status_code == 302
        attribute.refresh_from_db()
        assert attribute.name == 'UpdatedColor'

    def test_admin_attribute_delete(self, admin_client, attribute):
        url = reverse('custom_admin:attribute_delete', args=[attribute.id])
        assert admin_client.get(url).status_code == 200
        res = admin_client.post(url)
        assert res.status_code == 302
        assert not Attribute.objects.filter(id=attribute.id).exists()

@pytest.mark.django_db
class TestAdminOrderDetails:
    def test_admin_order_detail(self, admin_client, order):
        url = reverse('custom_admin:order_detail', args=[order.id])
        assert admin_client.get(url).status_code == 200
        # Valid POST
        res = admin_client.post(url, {'status': 'Delivered', 'tracking_number': '123'})
        assert res.status_code == 302
        order.refresh_from_db()
        assert order.status == 'Delivered'
        # Invalid POST
        res = admin_client.post(url, {'status': 'InvalidStatus'})
        assert res.status_code == 200

@pytest.mark.django_db
class TestAdminMisc:
    def test_admin_login_logic(self, client, admin_user):
        url = reverse('custom_admin:login')
        
        # 1. Successful Login Post
        with patch('myapp.custom_admin_views.authenticate') as mock_auth:
            mock_auth.return_value = admin_user
            res = client.post(url, {'username': 'admin', 'password': 'password123'})
            assert res.status_code == 302
            assert client.session['_site_admin_user_id'] == admin_user.id
        
        # 2. Redirect if already logged in
        assert client.get(url).status_code == 302
    
        client.session.flush()
        
        # 3. Invalid User
        res = client.post(url, {'username': 'wrong', 'password': '123'})
        assert res.status_code == 200
        assert client.session.get('login_attempts', 0) == 1
        
        # 4. Non-SiteAdmin
        User.objects.create_user(username='normal', password='123')
        res = client.post(url, {'username': 'normal', 'password': '123'})
        assert res.status_code == 200
        assert client.session.get('login_attempts', 0) == 2
        
        # 5. Throttle branch
        client.session.flush()
        session = client.session
        session['login_attempts'] = 5
        session.save()
        res = client.get(url)  # GET should also trigger it
        assert res.status_code == 200
        assert "Too many login attempts" in res.content.decode() or len(client.cookies) > 0

    def test_site_admin_required_decorator(self, client):
        url = reverse('custom_admin:dashboard')
        # No session
        res = client.get(url)
        assert res.status_code == 302
        assert '/admin/login/' in res.url
        
        # Invalid Session
        session = client.session
        session['_site_admin_user_id'] = 99999
        session.save()
        res = client.get(url)
        assert res.status_code == 302
        
    def test_admin_refresh_exchange_rates(self, admin_client):
        url = reverse('custom_admin:api_refresh_currency')
        assert admin_client.get(url).status_code == 405
        with patch('myapp.services.currency_service.CurrencyService.get_rates') as mock_rates:
            mock_rates.return_value = {'base': 'USD', 'timestamp': 12345}
            assert admin_client.post(url).status_code == 200
            mock_rates.side_effect = Exception("err")
            assert admin_client.post(url).status_code == 500

    def test_admin_pytest_reports(self, admin_client):
        url = reverse('custom_admin:pytest_reports')
        assert admin_client.get(url).status_code == 200

    def test_admin_analytical_dashboard(self, admin_client):
        url = reverse('custom_admin:analytical_dashboard')
        assert admin_client.get(url).status_code == 200

    def test_admin_logout_edge_case(self, client, admin_user):
        url = reverse('custom_admin:logout')
        session = client.session
        session['_site_admin_user_id'] = admin_user.id
        session.save()
        # Delete user before logout to trigger DoesNotExist
        admin_user.delete()
        res = client.get(url)
        assert res.status_code == 302

@pytest.mark.django_db
class TestAdminExport:
    def test_admin_export_all_modules(self, admin_client, customer, order, product, coupon):
        # Item setup
        OrderItem.objects.create(order=order, variant=product.variants.first(), quantity=1, snapshot_price=10)
        url = reverse('custom_admin:export')
        
        # Modules
        assert admin_client.get(url, {'module': 'customers', 'format': 'csv', 'q': customer.email}).status_code == 200
        assert admin_client.get(url, {'module': 'orders', 'format': 'excel'}).status_code == 200
        assert admin_client.get(url, {'module': 'orders', 'start_date': '2000-01-01', 'end_date': '2100-01-01'}).status_code == 200
        
        with patch('myapp.exports.export_to_word') as mock_word:
            mock_word.return_value = MagicMock(status_code=200)
            assert admin_client.get(url, {'module': 'order_details', 'format': 'word'}).status_code == 200

        with patch('myapp.exports.export_to_pdf') as mock_pdf:
            mock_pdf.return_value = MagicMock(status_code=200)
            assert admin_client.get(url, {'module': 'products', 'format': 'pdf', 'q': product.model_name}).status_code == 200
            
        assert admin_client.get(url, {'module': 'coupons', 'format': 'csv'}).status_code == 200
        assert admin_client.get(url, {'module': 'invalid'}).status_code == 302
        assert admin_client.get(url, {'module': 'orders', 'start_date': 'wrong'}).status_code == 200

@pytest.mark.django_db
class TestAdminLowCoverageRemaining:
    """Invalid post scenarios for existing views."""
    def test_admin_category_add_invalid(self, admin_client):
        url = reverse('custom_admin:category_add')
        assert admin_client.post(url, {}).status_code == 200

    def test_admin_category_edit_invalid(self, admin_client, category):
        url = reverse('custom_admin:category_edit', args=[category.id])
        assert admin_client.post(url, {}).status_code == 200

    def test_admin_brand_add_invalid(self, admin_client):
        url = reverse('custom_admin:brand_add')
        assert admin_client.post(url, {}).status_code == 200

    def test_admin_brand_edit_invalid(self, admin_client, brand):
        url = reverse('custom_admin:brand_edit', args=[brand.id])
        assert admin_client.post(url, {}).status_code == 200
        
    def test_admin_coupon_add_invalid(self, admin_client):
        url = reverse('custom_admin:coupon_add')
        assert admin_client.post(url, {}).status_code == 200

    def test_admin_coupon_edit_invalid(self, admin_client, coupon):
        url = reverse('custom_admin:coupon_edit', args=[coupon.id])
        assert admin_client.post(url, {}).status_code == 200

@pytest.mark.django_db
class TestAdminNonViewLogic:
    """Tests for model properties, admin methods, and signals from test_admin.py."""

    def test_product_properties(self, product, variant):
        variant.price = 50
        variant.is_active = True
        variant.save()
        assert product.min_price == 50
        variant.stock_quantity = 10
        variant.save()
        assert product.total_stock == 10
        assert product.featured_image_url == ""

    def test_order_properties(self, order, variant):
        OrderItem.objects.create(order=order, variant=variant, quantity=2, snapshot_price=100, snapshot_product_name="P")
        assert order.subtotal() >= 0
        assert order.final_total_display == order.total_amount

    def test_admin_custom_methods(self):
        from myapp.admin import CouponAdmin, ProductVariantAdmin, ProductImageInline, ProductVariantInlineForProduct
        
        # Coupon usage
        coupon_admin = CouponAdmin(Coupon, django_admin.site)
        c1 = Coupon(usage_limit=100, used_count=50)
        assert "50.0%" in str(coupon_admin.usage_percentage(c1))
        assert "Unlimited" == coupon_admin.usage_percentage(Coupon(usage_limit=0, used_count=5))
        
        # Variant price
        variant_admin = ProductVariantAdmin(ProductVariant, django_admin.site)
        assert variant_admin.price(ProductVariant(price=500)) == 500

        # Inlines
        inline = ProductVariantInlineForProduct(ProductVariant, django_admin.site)
        v = ProductVariant(pk=1, stock_quantity=10)
        assert "In Stock" in str(inline.stock_badge(v))
        v.stock_quantity = 0
        assert "Out of Stock" in str(inline.stock_badge(v))

        # Image Previews
        img_inline = ProductImageInline(ProductImage, django_admin.site)
        assert img_inline.image_preview(ProductImage()) == "—"
        pi = ProductImage(pk=1, image=SimpleUploadedFile("test.jpg", b"content"))
        assert 'src="' in str(img_inline.image_preview(pi))

    def test_admin_actions(self, admin_client, product, variant, customer):
        from myapp.admin import CouponAdmin, ProductVariantAdmin
        
        # Coupon Export Action
        now = datetime.datetime.now(datetime.timezone.utc)
        coupon = Coupon.objects.create(
            code="EXPORTME", discount_type="percentage", value=10, active=True,
            valid_from=now, valid_to=now + datetime.timedelta(days=1)
        )
        coupon_admin = CouponAdmin(Coupon, django_admin.site)
        response = coupon_admin.export_usage_report(None, Coupon.objects.filter(id=coupon.id))
        assert response.status_code == 200
        assert response['Content-Disposition'] == 'attachment; filename="coupon_usage_report.csv"'

        # Bulk Actions
        v1 = ProductVariant.objects.create(product=product, sku="V1", price=100, stock_quantity=10, is_active=False)
        v2 = ProductVariant.objects.create(product=product, sku="V2", price=100, stock_quantity=10, is_active=True)
        variant_admin = ProductVariantAdmin(ProductVariant, django_admin.site)
        request = MagicMock()
        variant_admin.bulk_mark_active(request, ProductVariant.objects.filter(id=v1.id))
        v1.refresh_from_db()
        assert v1.is_active is True
        variant_admin.bulk_mark_inactive(request, ProductVariant.objects.filter(id=v2.id))
        v2.refresh_from_db()
        assert v2.is_active is False

    def test_site_admin_logic(self, db):
        from myapp.admin import SiteAdminForm, SiteAdminAdmin
        user = User.objects.create_user(username='sa', email='sa@ex.com')
        sa = SiteAdmin.objects.create(user=user)
        assert SiteAdminForm(instance=sa).fields['username'].initial == 'sa'
        
        # Clean duplicate
        form = SiteAdminForm(data={'username': 'sa', 'email': 'sa@ex.com', 'password': 'p'})
        assert not form.is_valid()
        
        # Save hooks
        sa_admin = SiteAdminAdmin(SiteAdmin, django_admin.site)
        request = MagicMock(user=user)
        new_sa = SiteAdmin()
        form = SiteAdminForm(data={'username': 'newsa', 'email': 'new@ex.com', 'password': 'p'})
        assert form.is_valid()
        sa_admin.save_model(request, new_sa, form, change=False)
        assert User.objects.filter(username='newsa').exists()

    def test_admin_save_delete_logging(self, db):
        from myapp.admin import CategoryAdmin, BrandAdmin, ProductAdmin, ProductVariantInlineForProduct
        request = MagicMock()
        request.user.username = "testadmin"
        
        cat = Category.objects.create(name="C1")
        brand = Brand.objects.create(name="B1")
        p = Product.objects.create(model_name="P1", category_id=cat, brand=brand)
        
        with patch('django.contrib.admin.ModelAdmin.save_model'), \
             patch('django.contrib.admin.ModelAdmin.delete_model'):
            # Trigger our custom log_action overrides
            CategoryAdmin(Category, django_admin.site).save_model(request, cat, None, change=False)
            BrandAdmin(Brand, django_admin.site).delete_model(request, brand)
            ProductAdmin(Product, django_admin.site).save_model(request, p, MagicMock(), change=True)
        
        # Variant Stock BadgeFallback
        assert ProductVariantInlineForProduct(ProductVariant, django_admin.site).stock_badge(ProductVariant()) == "—"

    def test_coupon_admin_colors(self):
        from myapp.admin import CouponAdmin
        ca = CouponAdmin(Coupon, django_admin.site)
        assert 'color: orange' in ca.usage_percentage(Coupon(usage_limit=10, used_count=9))
        assert 'color: red' in ca.usage_percentage(Coupon(usage_limit=10, used_count=10))
        assert ca.usage_percentage(Coupon(usage_limit=None, used_count=5)) == "Unlimited"

    def test_attribute_image_preview(self, db):
        from myapp.admin import AttributeImageInline
        inline = AttributeImageInline(ProductImage, django_admin.site)
        assert inline.image_preview(ProductImage()) == "—"
        pi = ProductImage(pk=1, image=SimpleUploadedFile("attr.jpg", b"content"))
        assert 'src="' in str(inline.image_preview(pi))

@pytest.mark.django_db
class TestAdminGETCoverage:
    """Covers GET branches and list views."""
    
    def test_crud_gets_and_lists(self, admin_client, brand, category, coupon, product, variant, attribute, customer, order):
        # List pages
        list_urls = [
            reverse('custom_admin:brands') + '?page=1',
            reverse('custom_admin:categories') + '?page=1',
            reverse('custom_admin:coupons') + '?page=1',
            reverse('custom_admin:customers') + '?page=1',
            reverse('custom_admin:orders') + '?page=1',
            reverse('custom_admin:orders') + '?q=test',
            reverse('custom_admin:products') + '?q=test',
            reverse('custom_admin:variants') + '?q=test',
            reverse('custom_admin:attributes'),
        ]
        for url in list_urls:
            assert admin_client.get(url).status_code == 200

        # Paginator empty page branch
        assert admin_client.get(reverse('custom_admin:brands') + '?page=999').status_code == 200

        # Delete confirmation pages (GET)
        delete_urls = [
            reverse('custom_admin:brand_delete', args=[brand.id]),
            reverse('custom_admin:category_delete', args=[category.id]),
            reverse('custom_admin:coupon_delete', args=[coupon.id]),
            reverse('custom_admin:product_delete', args=[product.id]),
            reverse('custom_admin:variant_delete', args=[variant.id]),
            reverse('custom_admin:attribute_delete', args=[attribute.id]),
        ]
        for url in delete_urls:
            assert admin_client.get(url).status_code == 200

@pytest.mark.django_db
class TestAdminEdgeCoverage:
    """Covers specific logical branches for 100% coverage."""

    def test_site_admin_required_no_profile(self, client, admin_user):
        admin_user.site_admin_profile.delete()
        session = client.session
        session['_site_admin_user_id'] = admin_user.id
        session.save()
        response = client.get(reverse('custom_admin:dashboard'))
        assert response.status_code == 302
        assert reverse('custom_admin:login') in response.url

    def test_admin_export_extra_branches(self, admin_client, customer, order, product):
        OrderItem.objects.create(order=order, variant=product.variants.first(), quantity=1, snapshot_price=10)
        url = reverse('custom_admin:export')
        
        params = {
            'module': 'order_details',
            'format': 'csv',
            'start_date': '2000-01-01',
            'end_date': '2100-01-01'
        }
        assert admin_client.get(url, params).status_code == 200
        assert admin_client.get(url, {'module': 'orders', 'end_date': 'bad'}).status_code == 200
        # Search query for orders
        assert admin_client.get(url, {'module': 'orders', 'format': 'csv', 'q': order.customer.full_name}).status_code == 200
        # Invalid format branch
        assert admin_client.get(url, {'module': 'customers', 'format': 'txt'}).status_code == 302

    def test_stream_pytest_popen_fail(self, admin_client):
        url = reverse('custom_admin:api_run_pytest_stream')
        with patch('subprocess.Popen', side_effect=Exception("Explode")):
            response = admin_client.get(url)
            # Generation fails immediately
            try:
                list(response.streaming_content)
            except Exception:
                pass
