import os
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from playwright.sync_api import sync_playwright

def generate_invoice_pdf(order):
    """
    Generates a PDF invoice for the given order using Playwright.
    """
    context = {
        'order': order,
        'items': order.items.all(),
    }
    html_string = render_to_string('invoice.html', context)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_string)
        # Use A4 format and print background for colors/images
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
    
    return pdf_bytes

def send_order_email(order, event_type):
    """
    Sends an automated email notification based on the order lifecycle event.
    event_type can be: 'confirmation', 'shipping', 'out_for_delivery', 'delivered', 'cancelled', 'returned'
    """
    customer = order.customer
    subject = f"Electro - Order Update #{order.id}"
    
    template_map = {
        'confirmation': 'myapp/emails/order_confirmation.html',
        'shipping': 'myapp/emails/shipping_update.html',
        'out_for_delivery': 'myapp/emails/out_for_delivery.html',
        'delivered': 'myapp/emails/delivery_confirmation.html',
        'cancelled': 'myapp/emails/status_update.html',
        'returned': 'myapp/emails/status_update.html',
    }
    
    if event_type not in template_map:
        template_name = 'myapp/emails/status_update.html'
    else:
        template_name = template_map[event_type]
        
    subject_map = {
        'confirmation': f"Order Confirmation - Order #{order.id} Placed Successfully",
        'shipping': f"Your Order #{order.id} Has Been Shipped!",
        'out_for_delivery': f"Order #{order.id} Is Out For Delivery",
        'delivered': f"Order #{order.id} Delivered Successfully",
        'cancelled': f"Order #{order.id} Has Been Cancelled",
        'returned': f"Order #{order.id} Return Processed",
    }
    
    subject = subject_map.get(event_type, f"Update on your Order #{order.id}")
    
    context = {
        'order': order,
        'customer': customer,
        'event_type': event_type,
        'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'http://localhost:8000',
    }
    
    html_message = render_to_string(template_name, context)
    
    email = EmailMessage(
        subject,
        html_message,
        settings.EMAIL_HOST_USER,
        [customer.email],
    )
    email.content_subtype = "html"  # Main content is now text/html
    
    # Attach PDF invoice only for Order Confirmation
    if event_type == 'confirmation':
        try:
            pdf_content = generate_invoice_pdf(order)
            email.attach(f"Invoice_{order.id}.pdf", pdf_content, "application/pdf")
        except Exception as e:
            # Log error but don't stop email sending if PDF fails
            print(f"Error generating PDF: {e}")
            
    try:
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
