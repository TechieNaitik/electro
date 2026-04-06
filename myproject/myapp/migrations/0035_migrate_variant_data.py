"""
Phase 2 — Data Migration: Migrate variant_specs into structured variant tables.

Extend VARIANT_PARSE_MAP to cover all values present in your DB before running.
Run: SELECT DISTINCT variant_specs FROM myapp_product WHERE variant_specs != '';
to enumerate the values that need to be mapped.
"""
import logging
from django.db import migrations

VARIANT_PARSE_MAP = {
    # Maps lowercased token → (attribute_name, display_value)
    # Storage
    "32gb":   ("Storage", "32GB"),
    "64gb":   ("Storage", "64GB"),
    "128gb":  ("Storage", "128GB"),
    "256gb":  ("Storage", "256GB"),
    "512gb":  ("Storage", "512GB"),
    "1tb":    ("Storage", "1TB"),
    "2tb":    ("Storage", "2TB"),
    # RAM
    "4gb":    ("RAM", "4GB"),
    "6gb":    ("RAM", "6GB"),
    "8gb":    ("RAM", "8GB"),
    "12gb":   ("RAM", "12GB"),
    "16gb":   ("RAM", "16GB"),
    "32gb":   ("RAM", "32GB"),
    # Colors
    "blue":   ("Color", "Blue"),
    "black":  ("Color", "Black"),
    "white":  ("Color", "White"),
    "gold":   ("Color", "Gold"),
    "silver": ("Color", "Silver"),
    "red":    ("Color", "Red"),
    "green":  ("Color", "Green"),
    "grey":   ("Color", "Grey"),
    "gray":   ("Color", "Gray"),
    "pink":   ("Color", "Pink"),
    "purple": ("Color", "Purple"),
    "yellow": ("Color", "Yellow"),
    "orange": ("Color", "Orange"),
    # Connectivity
    "wi-fi":     ("Connectivity", "Wi-Fi Only"),
    "wifi":      ("Connectivity", "Wi-Fi Only"),
    "cellular":  ("Connectivity", "Wi-Fi + Cellular"),
    "lte":       ("Connectivity", "Wi-Fi + Cellular"),
    # SIM
    "dual":   ("Sim Slots", "Dual SIM"),
    "single": ("Sim Slots", "Single SIM"),
    # Size
    "s":   ("Size", "S"),
    "m":   ("Size", "M"),
    "l":   ("Size", "L"),
    "xl":  ("Size", "XL"),
    "xxl": ("Size", "XXL"),
}


def migrate_variants_forward(apps, schema_editor):
    log = logging.getLogger("variant_migration")
    Product          = apps.get_model('myapp', 'Product')
    Attribute        = apps.get_model('myapp', 'Attribute')
    AttributeValue   = apps.get_model('myapp', 'AttributeValue')
    ProductVariant   = apps.get_model('myapp', 'ProductVariant')
    VariantAttribute = apps.get_model('myapp', 'VariantAttribute')

    migrated = 0
    skipped  = 0

    for product in Product.objects.exclude(variant_specs='').exclude(variant_specs__isnull=True):
        tokens = [t.strip().lower() for t in product.variant_specs.split()]
        parsed   = []
        unparsed = []

        for token in tokens:
            if token in VARIANT_PARSE_MAP:
                parsed.append(VARIANT_PARSE_MAP[token])
            else:
                unparsed.append(token)

        if unparsed:
            log.warning(
                "Product pk=%s variant_specs=%r — unrecognised tokens: %s",
                product.pk, product.variant_specs, unparsed
            )

        if not parsed:
            skipped += 1
            continue  # nothing to migrate for this product

        sku = f"MIGRATED-{product.pk}"
        variant, created = ProductVariant.objects.get_or_create(
            product=product,
            sku=sku,
            defaults={
                'price': None,  # inherit from product.price
                'stock_quantity': product.stock_quantity,
                'reorder_threshold': product.reorder_threshold,
                'is_active': True,
            }
        )

        if created:
            for attr_name, attr_value in parsed:
                attr, _ = Attribute.objects.get_or_create(name=attr_name, category=None)
                av, _   = AttributeValue.objects.get_or_create(attribute=attr, value=attr_value)
                VariantAttribute.objects.get_or_create(variant=variant, attribute_value=av)
            migrated += 1

    log.info("Variant migration complete — migrated: %d, skipped: %d", migrated, skipped)
    print(f"[variant_migration] Migrated {migrated} products, skipped {skipped} (no mappable tokens).")


def migrate_variants_backward(apps, schema_editor):
    ProductVariant = apps.get_model('myapp', 'ProductVariant')
    deleted, _ = ProductVariant.objects.filter(sku__startswith='MIGRATED-').delete()
    print(f"[variant_migration] Backward: deleted {deleted} migrated variants.")


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0034_add_variant_schema"),
    ]

    operations = [
        migrations.RunPython(migrate_variants_forward, migrate_variants_backward),
    ]
