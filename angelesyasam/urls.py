from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound

# Güvenlik: .env ve diğer hassas dosyalara erişimi engelle
def block_sensitive_files(request, path):
    """Hassas dosyalara erişimi engelle"""
    return HttpResponseNotFound()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),
    path('sepet/', include('cart.urls')),
    path('siparisler/', include('orders.urls')),
    path('urunler/', include('products.urls')),
    path('odeme/', include('payments.urls')),
    path('', include('users.urls')),
    # Güvenlik: Hassas dosyalara erişimi engelle
    path('.env', block_sensitive_files),
    path('.env.local', block_sensitive_files),
    path('.env.production', block_sensitive_files),
    path('.git', block_sensitive_files),
    path('.git/', block_sensitive_files),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)