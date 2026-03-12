from django import forms
from .models import Category, Product

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category Name'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category_id', 'name', 'image', 'description', 'price', 'stock_quantity']
        widgets = {
            'category_id': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Product Name'}),
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
