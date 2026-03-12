from django.contrib import admin
from django.contrib.auth.models import User
from .models import Customer, Category, Product, Cart, Order, OrderItem, Wishlist, SiteAdmin

from django import forms

class SiteAdminForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, help_text="Enter unique username for the site admin.")
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=False, help_text="Required for new users.")

    class Meta:
        model = SiteAdmin
        fields = ('username', 'email', 'password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # If editing, username/email are read-only or pre-filled
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['password'].help_text = "Leave blank to keep current password."
            self.fields['password'].required = False

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not self.instance.pk and User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

@admin.register(SiteAdmin)
class SiteAdminAdmin(admin.ModelAdmin):
    form = SiteAdminForm
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')

    def save_model(self, request, obj, form, change):
        username = form.cleaned_data.get('username')
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        if not change:  # Creating new SiteAdmin
            user = User.objects.create_user(username=username, email=email, password=password)
            obj.user = user
        else:  # Updating existing SiteAdmin
            user = obj.user
            user.username = username
            user.email = email
            if password:
                user.set_password(password)
            user.save()
        
        super().save_model(request, obj, form, change)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'email', 'created_at')
    search_fields = ('full_name', 'email')
    readonly_fields = ('password', 'created_at')
    ordering      = ('-created_at',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_id', 'price', 'stock_quantity')
    search_fields = ('name',)
    list_filter = ('category_id',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'quantity')
    list_filter = ('customer',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'price', 'quantity')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_amount', 'payment_method', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('customer__full_name', 'customer__email', 'id')
    inlines = [OrderItemInline]

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'added_at')
    list_filter = ('customer', 'added_at')
