from django.db import models
from django.conf import settings
from products.models import Product
from orders.models import OrderSetting
from decimal import Decimal

class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, blank=True, null=True)  # for guest users
    created_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return sum(item.total_price() for item in self.items.all())

    def shipping_fee(self):
        settings = OrderSetting.objects.first()
        if not settings:
            return Decimal("0")

        if self.subtotal() >= settings.free_shipping_limit:
            return Decimal("0")

        return settings.shipping_fee

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Cart (Guest - Session {self.session_key})"

    def total_price(self):
        return self.subtotal() + self.shipping_fee()
    
    @property
    def free_shipping_limit(self):
        """Return the free shipping limit from OrderSetting"""
        settings = OrderSetting.objects.first()
        if settings:
            return settings.free_shipping_limit
        return Decimal("1000")  # Default value


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=50, blank=True, null=True, verbose_name="Beden")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Renk")
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('cart', 'product', 'size', 'color')


    def get_unit_price(self):
        """
        Return the discounted unit price if the campaign condition is met.
        """
        # Find the highest discount campaign for the product and quantity
        discount = self.product.bulk_discounts.filter(
            quantity_threshold__lte=self.quantity
        ).order_by('-discount_percent').first()

        if discount:
            # Calculate the discounted price: price * (1 - discount/100)
            reduction = Decimal(discount.discount_percent) / Decimal(100)
            return self.product.price * (Decimal(1) - reduction)
        
        return self.product.price

    def get_discount_info(self):
        """Return the discount status of the product and the quantity needed for the next discount."""
        all_discounts = self.product.bulk_discounts.all().order_by('quantity_threshold')
        current_discount = self.product.bulk_discounts.filter(
            quantity_threshold__lte=self.quantity
        ).order_by('-discount_percent').first()
    
        next_discount = self.product.bulk_discounts.filter(
            quantity_threshold__gt=self.quantity
        ).order_by('quantity_threshold').first()

        return {
            'applied': current_discount,
            'next': next_discount,
            'remaining_for_next': (next_discount.quantity_threshold - self.quantity) if next_discount else 0
        }

    @property
    def get_raw_total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        parts = [f"{self.quantity} x {self.product.name}"]
        if self.size:
            parts.append(f"Beden: {self.size}")
        if self.color:
            parts.append(f"Renk: {self.color}")
        return " - ".join(parts)

    def total_price(self):
        return self.get_unit_price() * self.quantity
