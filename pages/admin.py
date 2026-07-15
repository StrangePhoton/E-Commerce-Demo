from django.contrib import admin
from .models import HomeSlide

@admin.register(HomeSlide)
class HomeSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
    ordering = ('order',)
