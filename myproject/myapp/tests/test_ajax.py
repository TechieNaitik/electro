import pytest
from django.urls import reverse
from myapp.models import Cart, Wishlist, Product

@pytest.mark.django_db
class TestAjax:
    def test_update_cart_quantity_authenticated(self, client, customer, variant):
        session = client.session
        session['email'] = customer.email
        session.save()
        
        # First add to cart
        cart_item = Cart.objects.create(customer=customer, variant=variant, quantity=1)
        
        # path('update-cart/<int:cid>/<str:action>/', views.update_cart, name='update_cart')

        response = client.get(
            reverse('update_cart', args=[cart_item.id, 'increase']),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert Cart.objects.get(id=cart_item.id).quantity == 2


    def test_wishlist_toggle_authenticated(self, client, customer, variant):
        session = client.session
        session['email'] = customer.email
        session.save()
        
        product = variant.product
        response = client.get(reverse('toggle_wishlist', args=[product.id]))
        assert response.status_code == 200
        assert response.json()['action'] == 'added'
        assert Wishlist.objects.filter(customer=customer, variant=variant).exists()
        
        # Toggle Remove
        response = client.get(reverse('toggle_wishlist', args=[product.id]))
        assert response.status_code == 200
        assert response.json()['action'] == 'removed'
        assert not Wishlist.objects.filter(customer=customer, variant=variant).exists()
    def test_add_to_cart_ajax(self, client, customer, variant):
        session = client.session
        session['email'] = customer.email
        session.save()
        
        product = variant.product
        response = client.post(
            reverse('add_to_cart', args=[product.id]),
            {'variant_id': variant.id, 'qty': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert Cart.objects.filter(customer=customer, variant=variant).exists()
