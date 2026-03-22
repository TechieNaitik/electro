import pytest
from django.urls import reverse
from myapp.models import Customer, Product, Category

@pytest.mark.django_db
class TestViews:
    def test_home_view(self, client):
        response = client.get(reverse('home'))
        assert response.status_code == 200
        # Views might render 'index.html'
        assert 'index.html' in [t.name for t in response.templates]

    def test_shop_view(self, client):
        response = client.get(reverse('shop'))
        assert response.status_code == 200
        assert 'shop.html' in [t.name for t in response.templates]

    def test_product_detail_view(self, client, product):
        response = client.get(reverse('single', args=[product.id]))
        assert response.status_code == 200
        assert 'single.html' in [t.name for t in response.templates]
        assert response.context['product'] == product

    def test_login_view_get(self, client):
        response = client.get(reverse('login'))
        assert response.status_code == 200
        assert 'login.html' in [t.name for t in response.templates]

    def test_cart_view_redirects_if_not_logged_in(self, client):
        response = client.get(reverse('cart'))
        assert response.status_code == 302
        assert response.url == reverse('login')

    def test_login_success(self, client, customer):
        response = client.post(reverse('login'), {
            'email': customer.email,
            'password': customer.password
        })
        assert response.status_code == 302
        assert response.url == reverse('home')
        assert client.session['email'] == customer.email
