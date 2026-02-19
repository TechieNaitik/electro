from django.db import models

class Customer(models.Model):
    full_name  = models.CharField(max_length=50)
    email      = models.EmailField(unique=True)
    password   = models.CharField(max_length=21)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Customer'
        verbose_name_plural = 'Customers'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.full_name} <{self.email}>"
