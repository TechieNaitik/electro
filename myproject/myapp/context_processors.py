from .models import Cart, Customer, Wishlist

def cart_data(request):
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()
        if customer:
            cart_items = Cart.objects.filter(customer=customer)
            subtotal = sum(item.total_price() for item in cart_items)
            count = sum(item.quantity for item in cart_items)
            shipping = 100 * count
            total = subtotal + shipping
            return {
                'global_cart_count': count,
                'global_cart_total': total
            }
    return {
        'global_cart_count': 0,
        'global_cart_total': 0
    }

def wishlist_data(request):
    wishlist_ids = []
    if 'email' in request.session:
        customer = Customer.objects.filter(email=request.session['email']).first()
        if customer:
            wishlist_ids = list(Wishlist.objects.filter(customer=customer).values_list('variant__product_id', flat=True).distinct())
    return {'wishlist_ids': wishlist_ids}

