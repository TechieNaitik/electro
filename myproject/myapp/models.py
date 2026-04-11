from django.contrib.auth.models import User
import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

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

    sku         = models.CharField(max_length=50, unique=True, null=True, blank=True)
    image       = models.ImageField(upload_to='img/')
    description = models.TextField()
    price       = models.IntegerField()
    stock_quantity = models.PositiveIntegerField(default=50)
    reorder_threshold = models.PositiveIntegerField(default=10) # For KPI alerts
    is_featured = models.BooleanField(default=False)

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
        """Constructs the full product name: Brand + Model Name."""
        parts = []
        if self.brand:
            parts.append(self.brand.name)
        if self.model_name:
            parts.append(self.model_name)
        return " ".join(parts).strip() or "Unnamed Product"

    @property
    def all_images(self):
        """Returns a list of all associated image objects."""
        # Start with the main image
        imgs = []
        if self.image:
            # We wrap it in a simple object to match the structure of ProductImage
            # or just return the image field itself if we handle it in template
            imgs.append({'url': self.image.url, 'main': True})
        
        # Add additional images
        for extra in self.images.all():
            imgs.append({'url': extra.image_url, 'main': False})
        
        return imgs

    @property
    def featured_image_url(self):
        """Safely returns the URL of the main product image or an empty string if it doesn't exist."""
        try:
            return self.image.url
        except ValueError:
            return ""

    def __str__(self):
        parts = [self.full_name]
        if self.variant_specs:
            parts.append(self.variant_specs)
        return " ".join(parts).strip()

class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
        ]

class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant  = models.ForeignKey('ProductVariant', null=True, blank=True, on_delete=models.SET_NULL)   # Phase 1: nullable
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        # Use variant's effective_price if a variant is attached
        unit_price = self.variant.effective_price if self.variant else self.product.price
        return self.quantity * unit_price

    def __str__(self):
        variant_label = f" [{self.variant.sku}]" if self.variant else ""
        return f"{self.customer.full_name} - {self.product.full_name}{variant_label}"

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
        ('Exchanged', 'Exchanged'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Succeeded', 'Succeeded'),
        ('Failed', 'Failed'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_notes = models.TextField(blank=True, null=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending')
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    shipping_carrier = models.CharField(max_length=100, null=True, blank=True)
    carrier_url = models.URLField(null=True, blank=True)
    return_reason = models.TextField(null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        # Items sum + discount deduction = pre-discount subtotal
        return Decimal(str(self.total_amount)) - Decimal(str(self.shipping_charge)) + Decimal(str(self.discount_amount))

    @property
    def final_total_display(self):
        return Decimal(str(self.total_amount))

class OrderItem(models.Model):
    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant  = models.ForeignKey('ProductVariant', null=True, blank=True,
                                  on_delete=models.SET_NULL)
    # Snapshot fields — values captured at the moment of purchase so
    # the line item remains accurate even if variant/product is later modified.
    snapshot_sku        = models.CharField(max_length=100, blank=True)
    snapshot_price      = models.DecimalField(max_digits=10, decimal_places=2,
                                               null=True, blank=True)
    snapshot_attributes = models.JSONField(default=dict, blank=True)
    # e.g. {"Color": "Blue", "Storage": "256GB"}
    price    = models.IntegerField()   # keep for backward compat with existing orders
    quantity = models.PositiveIntegerField(default=1)

    def line_total(self):
        return self.price * self.quantity

class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant  = models.ForeignKey('ProductVariant', null=True, blank=True,
                                  on_delete=models.SET_NULL)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'product'], 
                condition=models.Q(variant__isnull=True),
                name='unique_customer_product_no_variant'
            ),
            models.UniqueConstraint(
                fields=['customer', 'product', 'variant'], 
                condition=models.Q(variant__isnull=False),
                name='unique_customer_product_variant'
            )
        ]

    def __str__(self):
        variant_label = f" [{self.variant.sku}]" if self.variant else ""
        return f"{self.customer.full_name} — {self.product.full_name}{variant_label}"

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

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [('percentage', 'Percentage'), ('fixed', 'Fixed Amount')]

    code                = models.CharField(max_length=50, unique=True)  # stored uppercase
    description         = models.CharField(max_length=255, blank=True)  # shown in admin
    discount_type       = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    value               = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from          = models.DateTimeField()
    valid_to            = models.DateTimeField()
    active              = models.BooleanField(default=True)
    usage_limit         = models.PositiveIntegerField(null=True, blank=True)  # None = unlimited
    used_count          = models.PositiveIntegerField(default=0)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stackable           = models.BooleanField(default=False)  # reserved for future use
    used_by_customers   = models.ManyToManyField(Customer, blank=True, related_name='used_coupons')

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def is_valid(self, cart_total, customer=None):
        now = timezone.now()
        if not self.active:
            return False, "This coupon is no longer active."
        if not (self.valid_from <= now <= self.valid_to):
            return False, "This coupon has expired."
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, "This coupon has reached its usage limit."
        if Decimal(str(cart_total)) < self.min_purchase_amount:
            return False, f"Spend at least ₹{self.min_purchase_amount} to use this coupon."
        if customer and self.used_by_customers.filter(id=customer.id).exists():
            return False, "You have already used this coupon."
        return True, ""

    @property
    def usage_percentage(self):
        if not self.usage_limit or self.usage_limit == 0:
            return 100 if self.used_count > 0 else 0
        return min(100, round((self.used_count / self.usage_limit) * 100, 1))

    @property
    def is_active_now(self):
        now = timezone.now()
        return self.active and (self.valid_from <= now <= self.valid_to)

    def calculate_discount(self, cart_total):
        cart_total = Decimal(str(cart_total))
        if self.discount_type == 'percentage':
            discount = cart_total * (self.value / Decimal('100'))
        else: # fixed
            discount = self.value
        
        # Cap discount at cart total
        if discount > cart_total:
            discount = cart_total
            
        return discount.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')

    def __str__(self):
        return self.code

@receiver(post_delete, sender=Product)
def delete_product_image_on_delete(sender, instance, **kwargs):
    """
    Deletes the associated image from the file system when a Product object is deleted.
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

class ProductImage(models.Model):
    product       = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant       = models.ForeignKey(
                        'ProductVariant', null=True, blank=True,
                        on_delete=models.SET_NULL,
                        related_name='variant_images'
                    )  # Specific to a variant
    attribute_value = models.ForeignKey(
                        'AttributeValue', null=True, blank=True,
                        on_delete=models.SET_NULL,
                        related_name='attribute_images'
                    )  # Specific to an attribute (e.g. Color=Blue)
    image         = models.ImageField(upload_to='img/')
    display_order = models.PositiveSmallIntegerField(default=0)
    alt_text      = models.CharField(max_length=200, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at']

    @property
    def image_url(self):
        """Safely returns the URL of this image or an empty string if it doesn't exist."""
        try:
            return self.image.url
        except ValueError:
            return ""

    def __str__(self):
        if self.variant:
            return f"Image for {self.variant.sku} (variant of {self.product.full_name})"
        return f"Image for {self.product.full_name}"

@receiver(post_delete, sender=ProductImage)
def delete_product_extra_image_on_delete(sender, instance, **kwargs):
    """
    Deletes the associated image from the file system when a ProductImage object is deleted.
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


# ===========================================================================
# VARIANT MODELS
# ===========================================================================

class Attribute(models.Model):
    """Represents a dimension of variation, optionally scoped to a category."""
    name          = models.CharField(max_length=100)
    category      = models.ForeignKey(
                        'Category', null=True, blank=True,
                        on_delete=models.SET_NULL,
                        related_name='attributes'
                    )  # None = global attribute (applies to all categories)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('name', 'category')
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """Represents a specific option within an attribute."""
    attribute     = models.ForeignKey(Attribute, on_delete=models.CASCADE,
                                      related_name='values')
    value         = models.CharField(max_length=100)   # e.g., "Blue", "256GB"
    hex_color     = models.CharField(max_length=7, blank=True)  # optional, for colour swatches
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('attribute', 'value')
        ordering = ['display_order', 'value']

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    """The purchasable unit — one record per unique combination of attribute values."""
    product        = models.ForeignKey('Product', on_delete=models.CASCADE,
                                       related_name='variants')
    attributes     = models.ManyToManyField(AttributeValue,
                                            through='VariantAttribute')
    sku            = models.CharField(max_length=100, unique=True)
    price          = models.DecimalField(max_digits=10, decimal_places=2,
                                         null=True, blank=True)
                                         # None = inherit from Product.price
    stock_quantity    = models.PositiveIntegerField(default=0)
    reorder_threshold = models.PositiveIntegerField(default=10)
    is_active      = models.BooleanField(default=True)

    @property
    def effective_price(self):
        """Returns the variant's own price, or falls back to the parent product price."""
        return self.price if self.price is not None else self.product.price

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    @property
    def gallery(self):
        """
        Returns all images scoped specifically to this variant AND images 
        scoped to its attribute values (like Color=Lavender).
        """
        # Specific variant images
        v_imgs = list(self.variant_images.all())
        
        # Shared attribute images (e.g., if an image is linked to the 'Lavender' Color)
        from .models import ProductImage # Internal import to avoid circular dependency if needed, though we are in models
        attr_imgs = list(ProductImage.objects.filter(
            product=self.product,
            attribute_value__in=self.attributes.all()
        ))
        
        # Merge and remove duplicates (by ID)
        merged = {img.id: img for img in (v_imgs + attr_imgs)}
        return sorted(merged.values(), key=lambda x: (x.display_order, x.created_at))

    @property
    def primary_image(self):
        """Returns the first variant image (including shared attribute images)."""
        gallery = self.gallery
        return gallery[0] if gallery else None

    @property
    def attribute_summary(self):
        """Returns a string summary of all attribute values (e.g. 'Color: Black, Storage: 256GB')."""
        return ", ".join([str(val) for val in self.attributes.all()])

    def __str__(self):
        return f"{self.product} — {self.sku}"


class VariantAttribute(models.Model):
    """Explicit through table for the M2M between ProductVariant and AttributeValue."""
    variant         = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    attribute_value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('variant', 'attribute_value')


@receiver(post_delete, sender=ProductVariant)
def delete_variant_images_on_delete(sender, instance, **kwargs):
    """Also delete variant images on disk when a ProductVariant is deleted."""
    for pi in instance.variant_images.all():
        if pi.image and os.path.isfile(pi.image.path):
            os.remove(pi.image.path)
        pi.delete()
