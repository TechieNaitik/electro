import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Product

products = Product.objects.all()
if not products:
    print("No products found.")
else:
    for p in products:
        print(f"Product: {p.name}, Stock: {p.stock_quantity}")
