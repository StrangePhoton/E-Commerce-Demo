# orders/models.py
from django.db import models
from django.conf import settings
from products.models import Product
from decimal import Decimal

class Order(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Taslak'),
        ('awaiting_contracts', 'Sözleşme Bekleniyor'),
        ('awaiting_payment', 'Ödeme Bekleniyor'),
        ('paid', 'Ödendi'),
        ('payment_failed', 'Ödeme Başarısız'),
        ('approved', 'Onaylandı'),
        ('preparing', 'Hazırlanıyor'),
        ('shipped', 'Kargoya Verildi'),
        ('delivered', 'Teslim Edildi'),
        ('cancelled', 'İptal Edildi'),
    ]

    PAYMENT_METHODS = (
        ("iyzico", "Iyzico"),
        ("akbank", "Akbank"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # 💰 Prices
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    cargo_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100  
    )

    
    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=20)
    shipping_district = models.CharField(max_length=100)

    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=50)
    shipping_country = models.CharField(max_length=30, default="Türkiye")

    # Billing Address Information
    billing_full_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Fatura Adı Soyadı')
    billing_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Fatura Telefon')
    billing_address = models.TextField(blank=True, null=True, verbose_name='Fatura Adresi')
    billing_city = models.CharField(max_length=50, blank=True, null=True, verbose_name='Fatura Şehir')
    billing_district = models.CharField(max_length=100, blank=True, null=True, verbose_name='Fatura İlçe')
    billing_country = models.CharField(max_length=30, default="Türkiye", blank=True, null=True, verbose_name='Fatura Ülke')
    
    pre_information_text = models.TextField(blank=True)
    distance_sales_contract_text = models.TextField(blank=True)

    pre_information_approved = models.BooleanField(default=False)
    distance_contract_approved = models.BooleanField(default=False)
    contracts_approved_at = models.DateTimeField(null=True, blank=True)

    contract_version = models.CharField(
        max_length=20,
        default="MS-2025-01"
    )

    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        null=True,
        blank=True
    )

    payment_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    e_invoice_uuid = models.CharField(
        max_length=64,
        blank=True,
        null=True
    )

    # Invoice Information
    INVOICE_TYPE_CHOICES = [
        ('individual', 'Bireysel'),
        ('corporate', 'Kurumsal'),
        ('sole_proprietor', 'Şahıs Şirketi'),
    ]
    
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        default='individual',
        verbose_name='Fatura Tipi'
    )
    
    tax_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Vergi Numarası'
    )
    
    invoice_identity_number = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        verbose_name='TC Kimlik Numarası (Fatura için)'
    )

    # Cancellation Information
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_orders'
    )
    cancellation_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.status}"

    @property
    def items_total(self):
        return sum(
            (item.price * item.quantity)
            for item in self.items.all()
    )

    def calculate_totals(self):
        items_total = self.items_total
        
        # Cargo fee calculation - free over 1000 TL
        try:
            order_setting = OrderSetting.objects.first()
            if order_setting:
                if items_total >= order_setting.free_shipping_limit:
                    self.cargo_price = Decimal("0")
                else:
                    self.cargo_price = order_setting.shipping_fee
            else:
                # If OrderSetting is not found, default check
                if items_total >= Decimal("1000"):
                    self.cargo_price = Decimal("0")
                else:
                    self.cargo_price = Decimal("100")
        except Exception:
            # If an error occurs, default check
            if items_total >= Decimal("1000"):
                self.cargo_price = Decimal("0")
            else:
                self.cargo_price = Decimal("100")
        
        self.total_price = (items_total + self.cargo_price).quantize(Decimal("0.01"))
        self.save(update_fields=["total_price", "cargo_price"])
        return self.total_price


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    cancelled_quantity = models.PositiveIntegerField(default=0)  # Cancelled quantity
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=50, blank=True, null=True, verbose_name="Beden")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Renk")

    @property
    def active_quantity(self):
        """Active (not cancelled) quantity"""
        return self.quantity - self.cancelled_quantity

    @property
    def is_fully_cancelled(self):
        """Is fully cancelled?"""
        return self.cancelled_quantity >= self.quantity

    @property
    def total_amount(self):
        return sum(
            (item.price * item.quantity)
            for item in self.items.all()
        )
    
    def __str__(self):
        parts = [f"{self.quantity}x {self.product.name}"]
        if self.size:
            parts.append(f"Beden: {self.size}")
        if self.color:
            parts.append(f"Renk: {self.color}")
        return " - ".join(parts) + f" (Order #{self.order.id})"


class OrderSetting(models.Model):
    shipping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100
    )
    free_shipping_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sipariş Ayarı"
        verbose_name_plural = "Sipariş Ayarları"

    def __str__(self):
        return "Genel Sipariş Ayarları"


class ReturnRequest(models.Model):
    """Return Request Model"""
    
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('approved', 'İade Onaylandı (MNG Kodu Verildi)'),
        ('received', 'Ürün Geldi, İnceleniyor'),
        ('rejected', 'Reddedildi'),
        ('completed', 'Tamamlandı'),
    ]

    REASON_CHOICES = [
        ('defective', 'Ürün Hatalı'),
        ('wrong_item', 'Yanlış Ürün'),
        ('not_as_described', 'Açıklamaya Uygun Değil'),
        ('damaged', 'Hasarlı Geldi'),
        ('size_issue', 'Beden Sorunu'),
        ('color_issue', 'Renk Sorunu'),
        ('other', 'Diğer'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='return_requests')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='return_requests'
    )
    
    quantity = models.PositiveIntegerField(default=1)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    reason_detail = models.TextField(blank=True, help_text="İade sebebi detayları")
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    admin_note = models.TextField(blank=True, help_text="Yönetici notu")
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_returns'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "İade Talebi"
        verbose_name_plural = "İade Talepleri"
        ordering = ['-created_at']

    def __str__(self):
        return f"İade Talebi #{self.id} - Sipariş #{self.order.id}"