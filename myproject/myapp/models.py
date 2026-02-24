from django.db import models

class Customer(models.Model):
    full_name  = models.CharField(max_length=50)
    email      = models.EmailField(unique=True)
    password   = models.CharField(max_length=21)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

class Category(models.Model):
    name       = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    name        = models.CharField(max_length=100)
    image       = models.ImageField(upload_to='img/')
    description = models.TextField()
    price       = models.IntegerField()

    def __str__(self):
        return self.name