from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from orders.models import Order

@login_required
def payment_start(request):
    order_id = request.session.get("checkout_order_id")

    if not order_id:
        messages.warning(request, "Invalid payment session.")
        return redirect("checkout-address")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # 🔒 Security: payment is not allowed without contracts approval
    if not (
        order.pre_information_approved
        and order.distance_contract_approved
    ):
        messages.error(
            request,
            "You must approve the contracts before making a payment."
        )
        return redirect("checkout-contracts")

    if request.method == "POST":
        method = request.POST.get("payment_method")

        if not method:
            messages.error(request, "You must select a payment method.")
            return redirect("payment-start")

        order.payment_method = method
        order.status = "awaiting_payment"
        order.save(update_fields=["payment_method", "status"])

        if method == "iyzico":
            return redirect("iyzico-init", order_id=order.id)

        if method == "akbank":
            return redirect("akbank-init", order_id=order.id)

    return render(request, "checkout/payment.html", {
        "order": order
    })
