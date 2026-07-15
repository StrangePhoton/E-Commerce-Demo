# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Address , ContactMessage

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Admin panel edit screen groups
    fieldsets = UserAdmin.fieldsets + (
        ('Ek Bilgiler', {'fields': ('tc_kimlik_no', 'phone_number', 'birth_date')}),
    )
    # List screen to show
    list_display = ['username', 'email', 'tc_kimlik_no', 'is_staff']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name','email','phone','subject']

admin.site.register(Address)
