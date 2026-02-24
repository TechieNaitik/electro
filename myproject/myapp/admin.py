from django.contrib import admin
from .models import Customer, Category, Product

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
    list_display = ('name', 'category_id', 'price')
    search_fields = ('name',)
    list_filter = ('category_id',)
