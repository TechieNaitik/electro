from django.contrib.auth.models import User
import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

class SiteAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='site_admin_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class Customer(models.Model):
    full_name  = models.CharField(max_length=50)
    email      = models.EmailField(unique=True)
    password   = models.CharField(max_length=21)
    phone      = models.CharField(max_length=15, null=True, blank=True)
    address    = models.TextField(null=True, blank=True)
    town_city  = models.CharField(max_length=100, null=True, blank=True)
    state      = models.CharField(max_length=100, null=True, blank=True)
    country    = models.CharField(max_length=100, null=True, blank=True)
    postcode_zip = models.CharField(max_length=20, null=True, blank=True)
    status     = models.CharField(max_length=20, default='Active', choices=[('Active', 'Active'), ('Inactive', 'Inactive'), ('Blocked', 'Blocked')])
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

class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand       = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    model_name  = models.CharField(max_length=100, null=True, blank=True)
    variant_specs = models.CharField(max_length=100, null=True, blank=True, help_text="e.g. 128GB Blue, Dual Sim")
    
    # Old name field — we keep this temporarily for data migration
    name        = models.CharField(max_length=100, null=True, blank=True)
    sku         = models.CharField(max_length=50, unique=True, null=True, blank=True)
    image       = models.ImageField(upload_to='img/')
    description = models.TextField()
    price       = models.IntegerField()
    stock_quantity = models.PositiveIntegerField(default=50)
    reorder_threshold = models.PositiveIntegerField(default=10) # For KPI alerts

    @property
    def rating(self):
        """Returns the average rating calculated from all user reviews."""
        from django.db.models import Avg
        avg = self.product_reviews.aggregate(Avg('rating'))['rating__avg']
        return float(avg) if avg else 0.0

    @property
    def rounded_rating(self):
        """Returns the rating rounded to the nearest 0.5."""
        return round(self.rating * 2) / 2

    @property
    def total_votes(self):
        """Returns the total number of reviews/votes."""
        return self.product_reviews.count()

    @property
    def full_name(self):
        """Constructs the full product name: Brand + Model + Variant"""
        parts = []
        if self.brand:
            parts.append(self.brand.name)
        if self.model_name:
            parts.append(self.model_name)
        if self.variant_specs:
            parts.append(self.variant_specs)
        
        # Fallback to old name if restructuring isn't done yet
        return " ".join(parts).strip() or self.name or "Unnamed Product"

    def __str__(self):
        return self.full_name

class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
        ]

class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.customer.full_name} - {self.product.name}"

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
        ('Exchanged', 'Exchanged'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_notes = models.TextField(blank=True, null=True)
    total_amount = models.IntegerField()
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending')
    shipping_charge = models.IntegerField(default=0)
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    shipping_carrier = models.CharField(max_length=100, null=True, blank=True)
    carrier_url = models.URLField(null=True, blank=True)
    return_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.total_amount - self.shipping_charge

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)

    def line_total(self):
        return self.price * self.quantity

class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'product')  # prevent duplicates

    def __str__(self):
        return f"{self.customer.full_name} — {self.product.name}"

class ProductReview(models.Model):
    """Stores detailed product reviews and ratings from individual users."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_reviews')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    rating = models.IntegerField()
    review_text = models.TextField()
    ip_address = models.GenericIPAddressField()
    session_key = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'ip_address']),
            models.Index(fields=['product', 'customer']),
        ]

    def __str__(self):
        return f"{self.name} - {self.product.full_name} ({self.rating} stars)"

@receiver(post_delete, sender=Product)
def delete_product_image_on_delete(sender, instance, **kwargs):
    """
    Deletes the associated image from the file system when a Product object is deleted.
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
