from django.urls import path
from . import views

urlpatterns = [
    path('favorilerim/', views.favorites_list, name='favorites'),
    path('favorilere-ekle/<int:product_id>/', views.add_to_favorites, name='add_to_favorites'),
    path('favorilerimden-kaldir/<int:product_id>/', views.remove_from_favorites, name='remove_from_favorites'),
    path('adres-duzenle/<int:address_id>/', views.edit_address, name='edit_address'),
    path('adres-sil/<int:address_id>/', views.delete_address, name='delete_address'),
    path('adres-ekle-ajax/', views.add_address_ajax, name='add_address_ajax'),
    path('profil-guncelle/', views.update_profile, name='update_profile'),
]
