import pytest
from myapp.services.forecasting import ForecastingService
from myapp.models import Order, OrderItem
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

@pytest.mark.django_db
class TestForecastingService:
    def test_predict_sales_no_data(self, product):
        result = ForecastingService.predict_sales(product_id=product.id, days_ahead=7)
        assert result['status'] == 'No historical data available'
        assert len(result['forecast']) == 7
        assert all(val == 0 for date, val in result['forecast'])

    def test_predict_sales_category(self, category):
        # Missed line 19
        result = ForecastingService.predict_sales(category_id=category.id, days_ahead=1)
        assert result['status'] == 'No historical data available'

    def test_predict_sales_insufficient_data(self, product, variant, customer):
        # Create 1 sale
        order = Order.objects.create(customer=customer, total_amount=100)
        OrderItem.objects.create(
            order=order, variant=variant, quantity=5, snapshot_price=Decimal('20.00'), snapshot_product_name="P"
        )
        
        result = ForecastingService.predict_sales(product_id=product.id, days_ahead=3)
        assert result['status'] == 'Insufficient data for regression, using average'
        assert len(result['forecast']) == 3
        assert all(val == 5 for date, val in result['forecast'])

    def test_predict_sales_regression_success(self, product, variant, customer):
        # Create sales over multiple days
        now = timezone.now()
        
        o1 = Order.objects.create(customer=customer, total_amount=100)
        o1.created_at = now - timedelta(days=2)
        o1.save()
        OrderItem.objects.create(order=o1, variant=variant, quantity=10, snapshot_price=10, snapshot_product_name="P")
        
        o2 = Order.objects.create(customer=customer, total_amount=200)
        o2.created_at = now - timedelta(days=1)
        o2.save()
        OrderItem.objects.create(order=o2, variant=variant, quantity=20, snapshot_price=10, snapshot_product_name="P")
        
        result = ForecastingService.predict_sales(product_id=product.id, days_ahead=5)
        assert result['status'] == 'Success'
        assert len(result['forecast']) == 5
        # 10, 20... next should be ~30
        assert result['forecast'][0][1] >= 20

    def test_analyze_low_stock_at_risk(self, product, variant, customer):
        # High demand, low stock
        now = timezone.now()
        variant.stock_quantity = 5
        variant.save()
        
        o1 = Order.objects.create(customer=customer, total_amount=100)
        o1.created_at = now - timedelta(days=2)
        o1.save()
        OrderItem.objects.create(order=o1, variant=variant, quantity=10, snapshot_price=10, snapshot_product_name="P")
        
        o2 = Order.objects.create(customer=customer, total_amount=200)
        o2.created_at = now - timedelta(days=1)
        o2.save()
        OrderItem.objects.create(order=o2, variant=variant, quantity=20, snapshot_price=10, snapshot_product_name="P")
        
        result = ForecastingService.analyze_low_stock(product)
        assert result['at_risk'] is True
        assert result['days_left'] > 0

    def test_analyze_low_stock_safe(self, product, variant, customer):
        # Low demand, high stock
        variant.stock_quantity = 1000
        variant.save()
        
        now = timezone.now()
        o1 = Order.objects.create(customer=customer, total_amount=10)
        o1.created_at = now - timedelta(days=1)
        o1.save()
        OrderItem.objects.create(order=o1, variant=variant, quantity=1, snapshot_price=10, snapshot_product_name="P")
        
        result = ForecastingService.analyze_low_stock(product)
        assert result['at_risk'] is False
        assert result['days_left'] == 30
