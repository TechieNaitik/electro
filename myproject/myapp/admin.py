from django.contrib import admin
from django.contrib.auth.models import User
from .models import Customer, Category, Product, Cart, Order, OrderItem, Wishlist, SiteAdmin, Brand, ProductImage, Coupon
from .logger import log_action
from django.utils.html import format_html

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
    
    def save_model(self, request, obj, form, change):
        if not change:
            log_action(f"Admin: {request.user.username}", "Created Category (Admin Panel)", f"Category: {obj.name}")
        else:
            log_action(f"Admin: {request.user.username}", "Updated Category (Admin Panel)", f"Category: {obj.name}")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        log_action(f"Admin: {request.user.username}", "Deleted Category (Admin Panel)", f"Category: {obj.name}")
        super().delete_model(request, obj)

class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ('model_name', 'variant_specs', 'category_id', 'price', 'stock_quantity')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [ProductInline]
    
    def save_model(self, request, obj, form, change):
        if not change:
            log_action(f"Admin: {request.user.username}", "Created Brand (Admin Panel)", f"Brand: {obj.name}")
        else:
            log_action(f"Admin: {request.user.username}", "Updated Brand (Admin Panel)", f"Brand: {obj.name}")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        log_action(f"Admin: {request.user.username}", "Deleted Brand (Admin Panel)", f"Brand: {obj.name}")
        super().delete_model(request, obj)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model_name', 'variant_specs', 'category_id', 'price', 'stock_quantity')
    search_fields = ('model_name', 'brand__name', 'variant_specs', 'sku')
    list_filter = ('brand', 'category_id')
    raw_id_fields = ('brand',)
    inlines = [ProductImageInline]
    
    def save_model(self, request, obj, form, change):
        if not change:
            log_action(f"Admin: {request.user.username}", "Created Product (Admin Panel)", f"Product: {obj.full_name}")
        else:
            log_action(f"Admin: {request.user.username}", "Updated Product (Admin Panel)", f"Product: {obj.full_name}")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        log_action(f"Admin: {request.user.username}", "Deleted Product (Admin Panel)", f"Product: {obj.full_name}")
        super().delete_model(request, obj)

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

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'valid_from', 'valid_to', 'active', 'used_count', 'usage_limit', 'usage_percentage')
    list_filter = ('discount_type', 'active', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')
    filter_horizontal = ('used_by_customers',)
    
    def usage_percentage(self, obj):
        if obj.usage_limit is None or obj.usage_limit == 0:
            return "Unlimited"
        percentage = (obj.used_count / obj.usage_limit) * 100
        color = 'black'
        if percentage >= 100: color = 'red'
        elif percentage >= 80: color = 'orange'
        return format_html('<span style="color: {};">{}%</span>', color, round(percentage, 1))
    usage_percentage.short_description = "Usage %"

    actions = ['export_usage_report']

    def export_usage_report(self, request, queryset):
        import csv
        from django.http import HttpResponse
        from django.db.models import Sum
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="coupon_usage_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Code', 'Used Count', 'Usage Limit', 'Status', 'Total Discount Issued'])
        
        for coupon in queryset:
            total_discount = Order.objects.filter(coupon=coupon).aggregate(Sum('discount_amount'))['discount_amount__sum'] or 0
            writer.writerow([
                coupon.code, 
                coupon.used_count, 
                coupon.usage_limit or 'Unlimited', 
                'Active' if coupon.active else 'Inactive',
                total_discount
            ])
        
        return response
    export_usage_report.short_description = "Export usage report (CSV)"
