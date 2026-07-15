from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser

from products.models import Product


class CustomUser(AbstractUser):
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=11, blank=True, null=True,unique=True)

    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)

    tc_kimlik_no = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        unique=True
    )

    def __str__(self):
        return self.username

class Address(models.Model):
    ADDRESS_TYPES = [
        ('shipping', 'Sipariş Adresi'),
        ('billing', 'Fatura Adresi'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='addresses'
    )

    title = models.CharField(max_length=50, verbose_name="Adres Başlığı", help_text="Örn: Evim, İş Yerim")
    
    address_type = models.CharField(
        max_length=10,
        choices=ADDRESS_TYPES,
        default='shipping'
    )

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)

    city = models.CharField(max_length=30)
    district = models.CharField(max_length=30)

    address_line = models.TextField()

    country = models.CharField(max_length=30, default="Türkiye")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}/{self.district} - {self.address_type}"
    
class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Same product cannot be added to favorites again

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "İletişim Mesajı"
        verbose_name_plural = "İletişim Mesajları"

    def __str__(self):
        return f"{self.name} - {self.subject}"