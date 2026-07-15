from django.urls import path
from . import views

urlpatterns = [
    path("admin/orders/", views.order_list_view, name="admin_order_list"),
    path("admin/orders/<int:order_id>/invoice/", views.generate_invoice_view, name="admin-generate-invoice"),
    path("admin/orders/<int:order_id>/contracts/", views.admin_order_contracts, name="admin-order-contracts"),
    path("checkout/address/", views.checkout_address, name="checkout-address"),
    path("checkout/contracts/", views.checkout_contracts, name="checkout-contracts"),
    path("checkout/payment/", views.payment_start, name="checkout-payment"),
    path("checkout/success/", views.order_success, name="checkout-success"),
    path("checkout/add-address/", views.add_address_ajax, name="checkout_add_address_ajax"),
    
    # Cancellation Operations
    path("orders/<int:order_id>/cancel-partial/", views.cancel_order_partial, name="cancel-order-partial"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel-order"),
    path("orders/<int:order_id>/items/<int:item_id>/cancel/", views.cancel_order_item, name="cancel-order-item"),
    
    # Return Requests
    path("orders/<int:order_id>/items/<int:item_id>/return/", views.create_return_request, name="create-return-request"),
    path("returns/", views.return_request_list, name="return-request-list"),
    path("returns/select-order/", views.select_order_for_return, name="select-order-for-return"),
    path("admin/returns/", views.admin_return_requests, name="admin-return-requests"),
    path("admin/returns/history/", views.admin_return_requests_history, name="admin-return-requests-history"),
    path("admin/returns/<int:request_id>/", views.admin_return_request_detail, name="admin-return-request-detail"),
]

