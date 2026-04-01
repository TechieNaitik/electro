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
        fields = ['category_id', 'brand', 'model_name', 'variant_specs', 'image', 'description', 'price', 'stock_quantity']
        widgets = {
            'category_id': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'model_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. iPhone 15'}),
            'variant_specs': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 128GB, Blue'}),
            'image': forms.FileInput(attrs={'class': 'form-input-file'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Product Description', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Price', 'min': 0}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Stock Quantity', 'min': 0}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean_stock_quantity(self):
        stock = self.cleaned_data.get('stock_quantity')
        if stock is not None and stock < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock

# Product Image Form & FormSet
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm, 
    extra=5, 
    can_delete=True
)
