from .models import Cart, Customer

def cart_data(request):
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()
        if customer:
            cart_items = Cart.objects.filter(customer=customer)
            subtotal = sum(item.total_price() for item in cart_items)
            shipping = 100 if subtotal > 0 else 0
            total = subtotal + shipping
            count = sum(item.quantity for item in cart_items)
            return {
                'global_cart_count': count,
                'global_cart_total': total
            }
    return {
        'global_cart_count': 0,
        'global_cart_total': 0
    }
