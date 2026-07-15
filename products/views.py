from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect
from .models import Product
from django.contrib import messages
from django.db.models import ProtectedError

# Create your views here.
def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'products/product_list.html',{'products': products})

def product_detail(request, pk):
    return render(request, 'products/product_detail.html')

@user_passes_test(lambda u: u.is_staff)
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False  # We are not deleting the product, we are just deactivating it
    product.save()
    
    messages.warning(request, f'"{product.name}" product is deactivated and archived. Past orders are preserved, so the physical deletion is not performed.')
    return redirect('admin-product-list')