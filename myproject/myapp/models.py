import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Customer(models.Model):
    full_name  = models.CharField(max_length=50)
    email      = models.EmailField(unique=True)
    password   = models.CharField(max_length=21)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

class Category(models.Model):
    name       = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    name        = models.CharField(max_length=100)
    image       = models.ImageField(upload_to='img/')
    description = models.TextField()
    price       = models.IntegerField()
    stock_quantity = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name

class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.customer.full_name} - {self.product.name}"

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255)
    town_city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postcode_zip = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    order_notes = models.TextField(blank=True, null=True)
    total_amount = models.IntegerField()
    payment_method = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)

class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'product')  # prevent duplicates

    def __str__(self):
        return f"{self.customer.full_name} — {self.product.name}"

@receiver(post_delete, sender=Product)
def delete_product_image_on_delete(sender, instance, **kwargs):
    """
    Deletes the associated image from the file system when a Product object is deleted.
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
