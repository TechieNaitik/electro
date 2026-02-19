from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'email', 'created_at')
    search_fields = ('full_name', 'email')
    readonly_fields = ('password', 'created_at')
    ordering      = ('-created_at',)

