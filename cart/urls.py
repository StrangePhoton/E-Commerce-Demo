from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_cart, name='view_cart'),
    path('ekle/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('guncelle/', views.update_cart, name='update_cart'),
    path('kaldir/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.go_to_checkout, name='cart-checkout'),
]
