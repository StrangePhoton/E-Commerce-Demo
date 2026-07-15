from django.urls import path
from products import views

urlpatterns = [
    path('admin/product/delete/<int:pk>/', views.admin_product_delete, name='admin-product-delete'),
]
