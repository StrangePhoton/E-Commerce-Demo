# products/admin.py
from django.contrib import admin
from .models import Product, ProductImage, Category, BulkDiscount, ProductRating
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

admin.site.register(Category)
admin.site.register(BulkDiscount)

@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at', 'updated_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'review')
    readonly_fields = ('created_at', 'updated_at')

class ProductImageFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                count += 1
        
        if count < 1:
            raise ValidationError("You must upload at least 1 image for a product.")
        if count > 5:
            raise ValidationError("You can upload at most 5 images for a product.")

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    formset = ProductImageFormSet
    extra = 1  # Show 1 empty field initially
    max_num = 5 # Technically don't allow more than 5

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ['name', 'category', 'price', 'stock']