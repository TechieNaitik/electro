from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from .email_utils import send_order_email
import threading

@receiver(pre_save, sender=Order)
def store_previous_status(sender, instance, **kwargs):
    """
    Stores the previous status of an order for comparison in post_save.
    """
    if instance.id:
        try:
            old_order = Order.objects.get(id=instance.id)
            instance._previous_status = old_order.status
        except Order.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

@receiver(post_save, sender=Order)
def trigger_order_emails(sender, instance, created, **kwargs):
    """
    Triggers automated email notifications based on order lifecycle events.
    Sends emails in a separate thread to avoid slowing down the response.
    """
    event_type = None

    if created:
        # Order Confirmation logic is moved to views.checkout to ensure items are created before email is sent
        pass
    else:
        # Check for status changes
        old_status = getattr(instance, '_previous_status', None)
        new_status = instance.status

        if old_status != new_status:
            if new_status == 'Shipped':
                event_type = 'shipping'
            elif new_status == 'Out for Delivery':
                event_type = 'out_for_delivery'
            elif new_status == 'Delivered':
                event_type = 'delivered'
            elif new_status in ['Cancelled', 'Returned', 'Exchanged']:
                event_type = new_status.lower()
            else:
                event_type = 'status_update'

    if event_type:
        # Send email in a background thread to prevent blocking the UI
        thread = threading.Thread(target=send_order_email, args=(instance, event_type))
        thread.start()
