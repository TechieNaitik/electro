import pytest
from django.urls import reverse, resolve
from myapp.views import home, shop, single

@pytest.mark.django_db
class TestUrls:
    def test_home_url_resolves(self):
        url = reverse('home')
        assert resolve(url).func == home

    def test_shop_url_resolves(self):
        url = reverse('shop')
        assert resolve(url).func == shop

    def test_product_detail_url_resolves(self, product):
        url = reverse('single', args=[product.id])
        assert resolve(url).func == single

    def test_cart_item_update_url_resolves(self):
        # path('update-cart/<int:cid>/<str:action>/', views.update_cart, name='update_cart')
        url = reverse('update_cart', args=[1, 'inc'])
        assert resolve(url).url_name == 'update_cart'
