from django.contrib import admin
from .models import Cart , CartItem

class CartAdmin(admin.ModelAdmin):
    list_display = ["id","user"]

admin.site.register(Cart,CartAdmin)
admin.site.register(CartItem)