import pytest
from unittest.mock import patch, MagicMock
from myapp.email_utils import generate_invoice_pdf, send_order_email
from myapp.models import Order

@pytest.fixture
def mock_order():
    order = MagicMock(spec=Order)
    order.id = 123
    order.customer.email = "customer@example.com"
    order.customer.full_name = "John Doe"
    # mock items.all()
    order.items.all.return_value = []
    return order

@pytest.mark.django_db
class TestEmailUtils:
    
    @patch('myapp.email_utils.sync_playwright')
    @patch('myapp.email_utils.render_to_string')
    def test_generate_invoice_pdf(self, mock_render, mock_playwright, mock_order):
        mock_render.return_value = "<html><body>Invoice</body></html>"
        
        # Mock playwright chain: p.chromium.launch().new_page().pdf()
        mock_p = mock_playwright.return_value.__enter__.return_value
        mock_browser = mock_p.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value
        mock_page.pdf.return_value = b"PDF_BYTES"
        
        pdf_bytes = generate_invoice_pdf(mock_order)
        
        assert pdf_bytes == b"PDF_BYTES"
        mock_render.assert_called_once()
        mock_page.set_content.assert_called_once_with("<html><body>Invoice</body></html>")

    @patch('myapp.email_utils.EmailMessage')
    @patch('myapp.email_utils.render_to_string')
    @patch('myapp.email_utils.generate_invoice_pdf')
    def test_send_order_email_confirmation(self, mock_gen_pdf, mock_render, mock_email_msg, mock_order):
        mock_render.return_value = "<html>Email Body</html>"
        mock_gen_pdf.return_value = b"PDF_BYTES"
        
        # Setup mock email instance
        mock_email_instance = mock_email_msg.return_value
        
        success = send_order_email(mock_order, 'confirmation')
        
        assert success is True
        mock_email_msg.assert_called_once()
        # Verify attachment
        mock_email_instance.attach.assert_called_once_with("Invoice_123.pdf", b"PDF_BYTES", "application/pdf")
        mock_email_instance.send.assert_called_once()

    @patch('myapp.email_utils.EmailMessage')
    @patch('myapp.email_utils.render_to_string')
    def test_send_order_email_shipping(self, mock_render, mock_email_msg, mock_order):
        mock_render.return_value = "<html>Shipping Body</html>"
        mock_email_instance = mock_email_msg.return_value
        
        success = send_order_email(mock_order, 'shipping')
        
        assert success is True
        # Shipping update should NOT have an attachment
        mock_email_instance.attach.assert_not_called()
        mock_email_instance.send.assert_called_once()

    @patch('myapp.email_utils.EmailMessage')
    @patch('myapp.email_utils.render_to_string')
    def test_send_order_email_failure(self, mock_render, mock_email_msg, mock_order):
        mock_render.return_value = "<html>Body</html>"
        mock_email_instance = mock_email_msg.return_value
        mock_email_instance.send.side_effect = Exception("SMTP Error")
        
        # This will print "Error sending email: SMTP Error" and return False
        success = send_order_email(mock_order, 'delivered')
        
        assert success is False

    def test_send_order_email_invalid_event(self, mock_order):
        # Test with an event type not in template_map
        with patch('myapp.email_utils.render_to_string') as mock_render:
            with patch('myapp.email_utils.EmailMessage') as mock_email_msg:
                send_order_email(mock_order, 'invalid_event')
                # Should fallback to emails/status_update.html
                mock_render.assert_called_once()
                args, kwargs = mock_render.call_args
                assert args[0] == 'emails/status_update.html'

    @patch('myapp.email_utils.EmailMessage')
    @patch('myapp.email_utils.render_to_string')
    @patch('myapp.email_utils.generate_invoice_pdf')
    def test_send_order_email_pdf_failure(self, mock_gen_pdf, mock_render, mock_email_msg, mock_order):
        mock_render.return_value = "<html>Email Body</html>"
        # Simulate PDF generation failure
        mock_gen_pdf.side_effect = Exception("PDF Gen Error")
        
        mock_email_instance = mock_email_msg.return_value
        
        success = send_order_email(mock_order, 'confirmation')
        
        # Email should still be sent even if PDF fails
        assert success is True
        mock_email_msg.assert_called_once()
        mock_email_instance.attach.assert_not_called()
        mock_email_instance.send.assert_called_once()
