# orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem

class OrderAdmin(admin.ModelAdmin):
    list_display = ["id","user","status","total_price","payment_method","created_at",]

admin.site.register(Order, OrderAdmin)

admin.site.register(OrderItem)
