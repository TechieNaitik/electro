from django import forms
from .models import Category, Product, Brand, ProductImage, Coupon
from django.forms import inlineformset_factory

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'description', 'discount_type', 'value', 'valid_from', 'valid_to', 'active', 'usage_limit', 'min_purchase_amount']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SAVE20'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional brief description'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': 0}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank for unlimited', 'min': 0}),
            'min_purchase_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fix for datetime-local input value display
        if self.instance and self.instance.valid_from:
            self.initial['valid_from'] = self.instance.valid_from.strftime('%Y-%m-%dT%H:%M')
        if self.instance and self.instance.valid_to:
            self.initial['valid_to'] = self.instance.valid_to.strftime('%Y-%m-%dT%H:%M')

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category Name'}),
        }

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Brand Name'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category_id', 'brand', 'model_name', 'description', 'is_featured']
        widgets = {
            'category_id': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'model_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. iPhone 15'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Product Description', 'rows': 4}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Product Image Form & FormSet
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'attribute_value', 'display_order', 'alt_text']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
            'attribute_value': forms.Select(attrs={'class': 'form-select'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-input', 'style': 'max-width: 80px;'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional alt text'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import AttributeValue
        self.fields['attribute_value'].queryset = AttributeValue.objects.select_related('attribute').order_by('attribute__name', 'value')
        self.fields['attribute_value'].empty_label = "General (All Variants)"

ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm, 
    extra=5, 
    can_delete=True
)

from .models import Attribute, AttributeValue, ProductVariant, VariantAttribute

class AttributeForm(forms.ModelForm):
    class Meta:
        model = Attribute
        fields = ['name', 'categories', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Color'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-control', 'style': 'height: 120px;'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class AttributeValueForm(forms.ModelForm):
    class Meta:
        model = AttributeValue
        fields = ['value', 'hex_color', 'display_order']
        widgets = {
            'value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Midnight'}),
            'hex_color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '#000000'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

AttributeValueFormSet = inlineformset_factory(
    Attribute,
    AttributeValue,
    form=AttributeValueForm,
    extra=5,
    can_delete=True
)

class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['product', 'sku', 'price', 'stock_quantity', 'reorder_threshold', 'is_active']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. IPH15-BLK-128'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'reorder_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean_stock_quantity(self):
        stock = self.cleaned_data.get('stock_quantity')
        if stock is not None and stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")
        return stock

class VariantAttributeForm(forms.ModelForm):
    class Meta:
        model = VariantAttribute
        fields = ['attribute_value']
        widgets = {
            'attribute_value': forms.Select(attrs={'class': 'form-control'}),
        }

VariantAttributeFormSet = inlineformset_factory(
    ProductVariant,
    VariantAttribute,
    form=VariantAttributeForm,
    extra=4,
    can_delete=True
)

