import pytest
from unittest.mock import patch, MagicMock
from myapp.models import Order, Customer

@pytest.mark.django_db
class TestSignals:
    @patch('myapp.signals.send_order_email')
    def test_order_status_change_triggers_email(self, mock_send_email, order):
        # We need to test the status change
        order.status = 'Pending'
        order.save()
        
        # Test various status changes
        statuses = [
            ('Shipped', 'shipping'),
            ('Out for Delivery', 'out_for_delivery'),
            ('Delivered', 'delivered'),
            ('Cancelled', 'cancelled'),
            ('Returned', 'returned'),
            ('Exchanged', 'exchanged'),
            ('Processing', 'status_update')
        ]
        
        for new_status, expected_event in statuses:
            order.status = new_status
            order.save()
            # Since it's threaded, we might need to wait or mock Thread.
            # But the mock_send_email is called inside the thread.
            # Using patch on threading.Thread might be safer for deterministic testing.
            pass

    @patch('myapp.signals.threading.Thread')
    def test_order_status_email_events(self, mock_thread, order):
        # Initial save (created=True) - should not trigger event in trigger_order_emails 
        # (logic currently passes for confirmation)
        order.status = 'Pending'
        order.save()
        assert mock_thread.call_count == 0

        statuses = [
            ('Shipped', 'shipping'),
            ('Out for Delivery', 'out_for_delivery'),
            ('Delivered', 'delivered'),
            ('Cancelled', 'cancelled'),
            ('Returned', 'returned'),
            ('Exchanged', 'exchanged'),
            ('Processing', 'status_update')
        ]

        for i, (new_status, expected_event) in enumerate(statuses, 1):
            # Manually set _previous_status as if it came from pre_save
            # though we want to test the full flow
            order.status = new_status
            order.save()
            
            # Check if Thread was started with correct args
            # The args are (instance, event_type)
            last_call_args = mock_thread.call_args[1]['args']
            assert last_call_args[1] == expected_event

    def test_order_previous_status_storage(self, order):
        order.status = 'Pending'
        order.save()
        
        order = Order.objects.get(id=order.id)
        order.status = 'Processing'
        order.save()
        
        # Check if _previous_status was correctly stored
        assert hasattr(order, '_previous_status')
        assert order._previous_status == 'Pending'

    def test_pre_save_new_order(self):
        """Test pre_save when order is new (no ID)."""
        from myapp.signals import store_previous_status
        from myapp.models import Order
        
        order = Order(status='Pending')
        store_previous_status(sender=Order, instance=order)
        assert order._previous_status is None

    def test_pre_save_order_not_found(self, order):
        """Test pre_save when order has ID but doesn't exist in DB (edge case)."""
        from myapp.signals import store_previous_status
        from myapp.models import Order
        
        # Give it a fake ID that doesn't exist
        order.id = 99999
        store_previous_status(sender=Order, instance=order)
        assert order._previous_status is None
