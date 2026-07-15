from django.urls import path
from .views import payment_start
from .iyzico import iyzico_init, iyzico_callback , iyzico_error , iyzico_success , iyzico_webhook

urlpatterns = [
    path("", payment_start, name="payment-start"),
    path("iyzico/init/<int:order_id>/", iyzico_init, name="iyzico-init"),
    path("iyzico/callback/", iyzico_callback, name="iyzico-callback"),
    path("iyzico/success/<int:order_id>/", iyzico_success, name="iyzico-success"),
    path("iyzico/error/", iyzico_error, name="iyzico-error"),
    path("iyzico/webhook/", iyzico_webhook),
]
