from django.db import models
from django.db.models import Avg
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from PIL import Image
import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    
    # Size and Color Features
    has_sizes = models.BooleanField(default=False, verbose_name="Beden Seçeneği Var mı?")
    has_colors = models.BooleanField(default=False, verbose_name="Renk Seçeneği Var mı?")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness by adding a counter to the slug
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(ratings.aggregate(Avg('rating'))['rating__avg'] or 0, 1)
        return 0.0

    def get_rating_count(self):
        return self.ratings.count()

    # Helper function to return the first image as the main image
    def get_main_image(self):
        main_img = self.images.all().first()
        if main_img:
            return main_img.image.url
        return None # Image not found (this will be prevented by the validator)
    
    def get_stock(self, size=None, color=None):
        """
        Return the stock status of the product.
        If variant exists, return the stock for the specified size/color.
        If variant does not exist, return the stock of the product itself.
        """
        if self.has_sizes or self.has_colors:
            # If variant exists
            if size or color:
                # Create filter
                filter_kwargs = {}
                if self.has_sizes and size:
                    filter_kwargs['size'] = size
                elif self.has_sizes:
                    filter_kwargs['size__isnull'] = True
                
                if self.has_colors and color:
                    filter_kwargs['color'] = color
                elif self.has_colors:
                    filter_kwargs['color__isnull'] = True
                
                variant = self.variants.filter(**filter_kwargs).first()
                if variant:
                    return variant.stock
                return 0
            # Total stock of all variants
            return sum(v.stock for v in self.variants.all())
        # If variant does not exist, return the stock of the product itself
        return self.stock
    
    @property
    def display_stock(self):
        """For display, return the stock - if variant exists, return the total stock, if not, return the stock of the product itself"""
        if self.has_sizes or self.has_colors:
            return sum(v.stock for v in self.variants.all())
        return self.stock
    
    def get_available_sizes(self):
        """Return the available sizes"""
        if not self.has_sizes:
            return []
        sizes = self.variants.exclude(size__isnull=True).exclude(size='').values_list('size', flat=True).distinct()
        return sorted(list(set(sizes)))
    
    def get_available_colors(self):
        """Return the available colors"""
        if not self.has_colors:
            return []
        colors = self.variants.exclude(color__isnull=True).exclude(color='').values_list('color', flat=True).distinct()
        return sorted(list(set(colors)))
    
    def get_variants_for_size(self, size):
        """Return the available colors for a specific size"""
        if not self.has_sizes or not size:
            return []
        colors = self.variants.filter(size=size, stock__gt=0).exclude(color__isnull=True).exclude(color='').values_list('color', flat=True).distinct()
        return sorted(list(colors))
    
    def get_variants_for_color(self, color):
        """Return the available sizes for a specific color"""
        if not self.has_colors or not color:
            return []
        sizes = self.variants.filter(color=color, stock__gt=0).exclude(size__isnull=True).exclude(size='').values_list('size', flat=True).distinct()
        return sorted(list(sizes))

class ProductVariant(models.Model):
    """Product variants - Stock management for size and color combinations"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50, blank=True, null=True, verbose_name="Beden")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Renk")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stok")
    
    class Meta:
        unique_together = ('product', 'size', 'color')
        verbose_name = "Ürün Varyantı"
        verbose_name_plural = "Ürün Varyantları"
        indexes = [
            models.Index(fields=['product', 'size', 'color']),
        ]
    
    def clean(self):
        """Variant validation"""
        if not self.product.has_sizes and self.size:
            raise ValidationError("This product does not have size options.")
        if not self.product.has_colors and self.color:
            raise ValidationError("This product does not have color options.")
        # Note: even if has_sizes or has_colors is True, the variant can be saved with empty size or color
        # Because in some variants, only size or only color can be present
    
    def __str__(self):
        parts = [self.product.name]
        if self.size:
            parts.append(f"Size: {self.size}")
        if self.color:
            parts.append(f"Color: {self.color}")
        return " - ".join(parts) if len(parts) > 1 else self.product.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='products/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            img_path = self.image.path
            img = Image.open(img_path)
            
            # Keep quality by converting to RGB
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Don't degrade quality by allowing up to 1200px width
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            
            # Highest quality setting (Quality 95)
            img.save(img_path, format='JPEG', optimize=True, quality=95)

class BulkDiscount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bulk_discounts")
    quantity_threshold = models.PositiveIntegerField()
    discount_percent = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name}: {self.quantity_threshold} adet => %{self.discount_percent}"

class ProductRating(models.Model):
    RATING_CHOICES = [(i, f'{i} Yıldız') for i in range(1, 6)]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_ratings')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    review = models.TextField(blank=True, null=True, help_text="İsteğe bağlı yorum")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating} Yıldız"

# 3. When product image is deleted, delete the physical image
@receiver(post_delete, sender=ProductImage)
def auto_delete_product_image_on_delete(sender, instance, **kwargs):
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

# When product image is updated, delete the old image
@receiver(pre_save, sender=ProductImage)
def auto_delete_product_image_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False
    try:
        old_file = sender.objects.get(pk=instance.pk).image
    except sender.DoesNotExist:
        return False
    new_file = instance.image
    if not old_file == new_file:
        if old_file and os.path.isfile(old_file.path):
            os.remove(old_file.path)