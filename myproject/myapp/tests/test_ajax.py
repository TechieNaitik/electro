import pytest
from django.urls import reverse
from myapp.models import Cart, Wishlist, Product

@pytest.mark.django_db
class TestAjax:
    def test_update_cart_quantity_authenticated(self, client, customer, product):
        session = client.session
        session['email'] = customer.email
        session.save()
        
        # First add to cart
        cart_item = Cart.objects.create(customer=customer, product=product, quantity=1)
        
        # path('update-cart/<int:cid>/<str:action>/', views.update_cart, name='update_cart')

        response = client.get(
            reverse('update_cart', args=[cart_item.id, 'increase']),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert Cart.objects.get(id=cart_item.id).quantity == 2


    def test_wishlist_toggle_authenticated(self, client, customer, product):
        session = client.session
        session['email'] = customer.email
        session.save()
        
        # path('toggle-wishlist/<int:pid>/', views.toggle_wishlist, name='toggle_wishlist')
        response = client.get(reverse('toggle_wishlist', args=[product.id]))
        assert response.status_code == 200
        assert response.json()['action'] == 'added'
        assert Wishlist.objects.filter(customer=customer, product=product).exists()
        
        # Toggle Remove
        response = client.get(reverse('toggle_wishlist', args=[product.id]))
        assert response.status_code == 200
        assert response.json()['action'] == 'removed'
        assert not Wishlist.objects.filter(customer=customer, product=product).exists()
