from decimal import Decimal
from django.utils import timezone
from ..models import Coupon, Customer

def apply_coupon(code: str, cart_total: Decimal, session: dict, customer: Customer = None) -> dict:
    """
    Validates and applies a coupon to the current cart.
    Returns: {"success": bool, "discount": Decimal, "new_total": Decimal, "message": str}
    """
    try:
        # Use case-insensitive lookup
        coupon = Coupon.objects.get(code__iexact=code.upper().strip(), active=True)
    except Coupon.DoesNotExist:
        return {
            "success": False,
            "message": "Invalid coupon code.",
            "discount": Decimal('0.00'),
            "new_total": cart_total
        }

    is_valid, message = coupon.is_valid(cart_total, customer=customer)
    if not is_valid:
        if 'coupon_id' in session:
            del session['coupon_id']
        return {
            "success": False,
            "message": message,
            "discount": Decimal('0.00'),
            "new_total": cart_total
        }

    discount = coupon.calculate_discount(cart_total)
    new_total = cart_total - discount
    
    # Store in session
    session['coupon_id'] = coupon.pk
    
    return {
        "success": True,
        "discount": discount,
        "new_total": new_total,
        "message": f"Coupon '{coupon.code}' applied! You saved ₹{discount}"
    }

def get_applied_coupon(session: dict):
    coupon_id = session.get('coupon_id')
    if coupon_id:
        try:
            return Coupon.objects.get(pk=coupon_id, active=True)
        except Coupon.DoesNotExist:
            if 'coupon_id' in session:
                del session['coupon_id']
    return None

def clear_coupon(session: dict):
    if 'coupon_id' in session:
        del session['coupon_id']
