from django.contrib.auth.models import User
import os
from django.db import models
from django.db.models.signals import post_delete, pre_delete
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
    description = models.TextField()
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
        """Returns a list of all associated image objects from variants and ProductImage."""
        imgs = []
        # 1. Images attached directly to Product (ProductImage model)
        # These include both general images (attr_value=None) and color-scoped ones.
        for extra in self.images.all():
            imgs.append({
                'url': extra.image_url, 
                'main': extra.display_order == 0,
                'av_id': extra.attribute_value_id  # Include color/attr id
            })
        return imgs

    @property
    def featured_image_url(self):
        """Safely returns the URL of the first available image."""
        # Try ProductImage first
        first_img = self.images.all().first()
        if first_img:
            return first_img.image_url
        
        # Fallback to variant images (though they should be in self.images.all() anyway)
        return ""

    @property
    def total_stock(self):
        """Returns the aggregate stock across all variants."""
        return sum(v.stock_quantity for v in self.variants.all())

    @property
    def min_price(self):
        """Returns the minimum price among all active variants."""
        prices = [v.price for v in self.variants.filter(is_active=True) if v.price is not None]
        return min(prices) if prices else 0

    def __str__(self):
        return self.full_name

    def get_option_types(self):
        """
        Returns a JSON-serializable list of attributes and their available values for this product.
        Used to build the frontend option selectors.
        """
        from .models import Attribute
        # Fetch attributes that have values associated with this product's variants
        attributes = Attribute.objects.filter(
            values__productvariant__product=self
        ).distinct().order_by('display_order', 'name').prefetch_related('values')

        data = []
        for attr in attributes:
            # Filter values to only those actually present for this product's variants
            relevant_values = attr.values.filter(productvariant__product=self).distinct().order_by('display_order', 'value')
            data.append({
                'id': attr.id,
                'name': attr.name,
                'values': [
                    {
                        'id': v.id,
                        'value': v.value,
                        'hex_color': v.hex_color or None
                    } for v in relevant_values
                ]
            })
        return data

    def get_variant_matrix(self):
        """
        Returns an O(1) lookup dictionary keyed by sorted attribute value IDs.
        e.g., {"3,7": {"price": "999.00", "stock": 10, ...}}
        Optimized with prefetch_related to avoid N+1 queries.
        """
        matrix = {}
        # Prefetch variants with their attributes ordered by attribute ID for consistent key generation
        variants = self.variants.filter(is_active=True).prefetch_related(
            'variantattribute_set__attribute_value__attribute'
        )
        
        for v in variants:
            # Generate a consistent key based on sorted attribute value IDs
            # Ordering by attribute__id ensures "Color,Storage" vs "Storage,Color" consistency
            attr_ids = sorted([
                va.attribute_value.id for va in v.variantattribute_set.all()
            ])
            key = ",".join(map(str, attr_ids))
            
            matrix[key] = {
                'id': v.id,
                'sku': v.sku,
                'price': str(v.price),
                'stock_quantity': v.stock_quantity,
                'in_stock': v.stock_quantity > 0,
                'attributes': {
                    va.attribute_value.attribute.name: va.attribute_value.value 
                    for va in v.variantattribute_set.all()
                }
            }
        return matrix

    def get_color_image_map(self):
        """
        Returns a mapping of attribute value IDs (usually colors) to their specific images.
        """
        color_map = {}
        # Fetch all product images that have an attribute value (color-scoped)
        images = self.images.exclude(attribute_value=None).select_related('attribute_value')
        for img in images:
            av_id = str(img.attribute_value_id) # Using string keys for JS compatibility
            if av_id not in color_map:
                color_map[av_id] = []
            color_map[av_id].append(img.image_url)
        return color_map

class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
        ]

class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    variant  = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['customer', 'variant'], name='unique_customer_variant_cart')
        ]
        indexes = [
            models.Index(fields=['customer', 'variant']),
        ]

    @property
    def unit_price(self):
        """Returns the variant price."""
        return self.variant.price

    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.customer.full_name} - {self.variant.product.full_name} [{self.variant.sku}]"

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
    variant  = models.ForeignKey('ProductVariant', null=True, blank=True,
                                  on_delete=models.SET_NULL)
    # Snapshot fields — values captured at the moment of purchase so
    # the line item remains accurate even if variant/product is later modified.
    snapshot_product_name = models.CharField(max_length=255, blank=True)
    snapshot_sku          = models.CharField(max_length=100, blank=True)
    snapshot_price        = models.DecimalField(max_digits=10, decimal_places=2,
                                                 null=True, blank=True)
    snapshot_attributes   = models.JSONField(default=dict, blank=True)
    # snapshot_price should be used exclusively for calculations
    quantity = models.PositiveIntegerField(default=1)

    def line_total(self):
        """Uses the Decimal snapshot_price for all calculations."""
        base_price = self.snapshot_price if self.snapshot_price is not None else Decimal('0.00')
        return base_price * self.quantity

class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    variant  = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, related_name='wishlist_items')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'variant'], 
                name='unique_customer_variant_wishlist'
            )
        ]

    def __str__(self):
        return f"{self.customer.full_name} — {self.variant.product.full_name} [{self.variant.sku}]"

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

class ProductImage(models.Model):
    product       = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
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
        if self.attribute_value:
            return f"Image for {self.product.full_name} ({self.attribute_value.value})"
        return f"Image for {self.product.full_name} (General)"

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
    """Represents a dimension of variation (e.g., Color), applicable across multiple categories."""
    name          = models.CharField(max_length=100)
    categories    = models.ManyToManyField(
                        'Category', blank=True,
                        related_name='attributes'
                    )  # Empty = global attribute (applies to all categories)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
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
    price          = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock_quantity    = models.PositiveIntegerField(default=0)
    reorder_threshold = models.PositiveIntegerField(default=10)
    is_active      = models.BooleanField(default=True)

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    @property
    def variant_image_url(self):
        """Attempts to find an image matching one of this variant's attributes (e.g. Color). Returns the product's featured image otherwise."""
        # Try to find a ProductImage that matches one of our attribute values
        # We prefetch_related for performance in bulk lookups
        for av in self.attributes.all():
            img = self.product.images.filter(attribute_value=av).first()
            if img:
                return img.image_url
        return self.product.featured_image_url

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

    def __str__(self):
        return f"{self.variant.sku} - {self.attribute_value}"


@receiver(pre_delete, sender=ProductVariant)
def delete_variant_images_on_delete(sender, instance, **kwargs):
    """
    Cleans up color-scoped images that were uniquely associated with this variant's attributes.
    Prevents AttributeError logs by using the correct reverse relationships.
    """
    try:
        # Get attributes before the variant is deleted
        attributes = list(instance.attributes.all())
        for av in attributes:
            # Check if any OTHER variant of this product still uses this attribute value
            other_variants_exist = instance.product.variants.exclude(id=instance.id).filter(attributes=av).exists()
            if not other_variants_exist:
                # No other variant uses this color/size, delete images scoped to it for this product
                for pi in instance.product.images.filter(attribute_value=av):
                    pi.delete() # Triggers file system deletion
    except (AttributeError, Exception):
        # Fail gracefully during bulk deletions or if relationships are already severed
        pass
