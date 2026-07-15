import os

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q
import logging 

# reduce_order_stock function in payments.iyzico module, import if needed

from cart.views import get_or_create_cart
from orders.gib_client import GibClient
from payments.iyzico import reduce_order_stock
from users.models import Address
from .models import Order, OrderItem, ReturnRequest
from .contracts import (
    generate_pre_information_text,
    generate_distance_sales_contract,
)
from cart.models import Cart, CartItem
from pages.forms import AddressForm
from django.http import JsonResponse

def get_user_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).first()
    return None

def attach_cart_items_to_order(cart, order):
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.get_unit_price(),
            size=item.size,
            color=item.color
        )

@login_required
def checkout_contracts(request):
    order_id = request.session.get("checkout_order_id")
    if not order_id:
        return redirect("checkout-address")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # WRONG LINES FIXED LIKE THIS:
    # We are only sending 'order', because contracts.py now only expects this.
    pre_info_text = generate_pre_information_text(order)
    distance_contract_text = generate_distance_sales_contract(order)

    # If contracts are already approved, reject POST requests
    contracts_approved = order.pre_information_approved and order.distance_contract_approved

    if request.method == "POST":
        # If already approved, do not allow re-approval
        if contracts_approved:
            messages.info(request, "Sözleşmeler zaten onaylanmış. Ödeme sayfasına yönlendiriliyorsunuz.")
            return redirect("checkout-payment")

        # Check approval checkboxes
        if not request.POST.get("pre_info") or not request.POST.get("distance_contract"):
            messages.error(request, "Devam etmek için sözleşmeleri onaylamalısınız.")
            # If an error occurs, show the form again, send the texts again
            return render(request, "checkout/contracts.html", {
                "order": order,
                "pre_info_text": pre_info_text,
                "distance_contract_text": distance_contract_text,
                "contracts_approved": contracts_approved,
            })

        # Process approved texts and signatures to the database
        order.pre_information_text = pre_info_text
        order.distance_sales_contract_text = distance_contract_text
        order.pre_information_approved = True
        order.distance_contract_approved = True
        order.contracts_approved_at = timezone.now()
        order.status = "awaiting_payment"
        order.save()

        return redirect("checkout-payment")

    return render(request, "checkout/contracts.html", {
        "order": order,
        "pre_info_text": pre_info_text,
        "distance_contract_text": distance_contract_text,
        "contracts_approved": contracts_approved,
    })

@login_required
def checkout_address(request):
    # Cart retrieval logic (according to get_or_create_cart function)
    cart = get_or_create_cart(request)

    if not cart or not cart.items.exists():
        return redirect("view_cart")
    
    # Check and remove inactive items in the cart
    inactive_items = []
    for item in cart.items.all():
        if not item.product.is_active:
            inactive_items.append(item.product.name)
            item.delete()
    
    if inactive_items:
        messages.error(request, f"Sepetinizdeki şu ürünler artık satışta değil ve sepetten kaldırıldı: {', '.join(inactive_items)}")
        return redirect("view_cart")

    # Get existing addresses - separate by type
    shipping_addresses = Address.objects.filter(user=request.user, address_type='shipping')
    billing_addresses = Address.objects.filter(user=request.user, address_type='billing')
    
    # Empty form object for the form in the modal
    address_form = AddressForm()

    # Check if there is an existing order, check the contract approval status
    contracts_approved = False
    order_id = request.session.get("checkout_order_id")
    if order_id:
        try:
            existing_order = Order.objects.get(id=order_id, user=request.user)
            contracts_approved = existing_order.pre_information_approved and existing_order.distance_contract_approved
        except Order.DoesNotExist:
            pass

    if request.method == "POST":
        # Get the selected address IDs
        shipping_id = request.POST.get("shipping_address")
        billing_id = request.POST.get("billing_address")
        same_as_shipping = request.POST.get("same_as_shipping") == 'on'

        # Get the shipping address object
        shipping_obj = get_object_or_404(Address, id=shipping_id, user=request.user)
        
        # Determine which object to use for the billing address
        if same_as_shipping:
            # If "same as shipping" is selected, use the shipping address
            billing_obj = shipping_obj
        else:
            # If "same as shipping" is not selected, use the selected billing address
            # billing_id can be empty (if the user did not select a billing address)
            if billing_id:
                billing_obj = get_object_or_404(Address, id=billing_id, user=request.user)
            else:
                # If the billing address is not selected, use the shipping address (fallback)
                billing_obj = shipping_obj

        # Billing information
        invoice_type = request.POST.get("invoice_type", "individual")
        tax_number = request.POST.get("tax_number", "").strip()
        invoice_identity_number = request.POST.get("invoice_identity_number", "").strip()
        
        # Validation
        if invoice_type in ['corporate', 'sole_proprietor'] and not tax_number:
            messages.error(request, "Kurumsal veya şahıs şirketi için vergi numarası gereklidir.")
            return render(request, "checkout/address.html", {
                "shipping_addresses": shipping_addresses,
                "billing_addresses": billing_addresses,
                "address_form": address_form,
                "contracts_approved": contracts_approved,
            })
        
        if not invoice_identity_number or len(invoice_identity_number) != 11:
            messages.error(request, "Geçerli bir TC kimlik numarası giriniz (11 haneli).")
            return render(request, "checkout/address.html", {
                "shipping_addresses": shipping_addresses,
                "billing_addresses": billing_addresses,
                "address_form": address_form,
                "contracts_approved": contracts_approved,
            })
        
        # Calculate shipping fee - from cart
        cargo_price = cart.shipping_fee()
        
        # 🚀 CREATE ORDER (The field names in your model should match exactly)
        order = Order.objects.create(
            user=request.user,
            status="awaiting_contracts",
            total_price=cart.total_price(),
            cargo_price=cargo_price,  # Shipping fee from cart
            
            # Shipping Information (Snapshot)
            shipping_full_name=shipping_obj.full_name,
            shipping_phone=shipping_obj.phone,
            shipping_city=shipping_obj.city,
            shipping_district=shipping_obj.district,
            shipping_address=shipping_obj.address_line,
            shipping_country=shipping_obj.country,
            
            # Billing Address Information (Snapshot)
            billing_full_name=billing_obj.full_name,
            billing_phone=billing_obj.phone,
            billing_city=billing_obj.city,
            billing_district=billing_obj.district,
            billing_address=billing_obj.address_line,
            billing_country=billing_obj.country,
            
            # Billing Information
            invoice_type=invoice_type,
            tax_number=tax_number if tax_number else None,
            invoice_identity_number=invoice_identity_number,
        )

        # Attach products
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.get_unit_price() # Fix the price at the order time
            )
        
        # Recalculate the total amount (after products are added)
        order.calculate_totals()

        # Session and redirect
        request.session["checkout_order_id"] = order.id
        return redirect("checkout-contracts")

    return render(request, "checkout/address.html", {
        "shipping_addresses": shipping_addresses,
        "billing_addresses": billing_addresses,
        "address_form": address_form,
        "contracts_approved": contracts_approved,
    })

# AJAX Address Save View
@login_required
def add_address_ajax(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            # Save the form, first get the data
            address_instance = form.save(commit=False)
            address_instance.user = request.user
            
            # Get the address type from POST (shipping or billing)
            address_type = request.POST.get('address_type', 'shipping')
            address_instance.address_type = address_type
            address_instance.save()
            
            # If the shipping address is being added and the user selects "same as shipping",
            # the billing address can be automatically created, but we are only saving the selected type for now

            return JsonResponse({
                "success": True,
                "address": {
                    "id": address_instance.id,
                    "title": address_instance.title,
                    "full_name": address_instance.full_name,
                    "city": address_instance.city,
                    "district": address_instance.district,
                    "address_line": address_instance.address_line,
                    "address_type": address_instance.address_type,
                }
            })
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "message": "Invalid method"})



@login_required
def payment_start(request):
    order_id = request.session.get("checkout_order_id")

    if not order_id:
        return redirect("checkout-address")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if the contracts are approved
    if not (order.pre_information_approved and order.distance_contract_approved):
        messages.error(request, "Ödeme sayfasına geçmek için önce sözleşmeleri onaylamalısınız.")
        return redirect("checkout-contracts")

    # here comes iyzico / stripe / transfer

    return render(request, "checkout/payment.html", {
        "order": order
    })

@login_required
def order_success(request):
    order_id = request.session.pop("checkout_order_id", None)

    if not order_id:
        return redirect("home")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # clear the cart
    CartItem.objects.filter(cart__user=request.user).delete()

    order.status = "paid"
    order.save(update_fields=["status"])
    
    # Reduce stock (if not reduced before)
    try:
        reduce_order_stock(order)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Failed to reduce stock in order_success: %s", str(e))

    return render(request, "checkout/success.html", {
        "order": order
    })


@staff_member_required
def order_list_view(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, "management/admin-order-list.html", {"orders": orders})

@staff_member_required
def generate_invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    invoice_data = build_invoice_data(order)
    client = GibClient(username=os.getenv("GIB_USERNAME", ""),password=os.getenv("GIB_PASSWORD", ""),test_mode=True,)

    try:
        client.login()
        response = client.create_invoice(invoice_data)
        uuid = response.get("uuid")
        if uuid:
            order.e_invoice_uuid = uuid
            order.save()

            html_content = client.get_invoice_html(uuid)
            client.send_invoice_email(order, html_content)

            messages.success(request, f"E-Fatura oluşturuldu ve gönderildi. UUID: {uuid}")
        else:
            messages.warning(request, "Fatura oluşturuldu ama UUID alınamadı.")

    except Exception as e:
        messages.error(request, f"E-Fatura oluşturulamadı: {str(e)}")

    finally:
        client.logout()

    return redirect("admin-order-list")

def build_invoice_data(order):
    items = []
    for item in order.items.all():
        items.append({
            "malHizmet": item.product.name,
            "miktar": item.quantity,
            "birimFiyat": float(item.price),
            "kdvOrani": 18,
        })

    customer_name = order.user.get_full_name() if order.user else order.guest_email

    invoice_data = {
        "tarih": order.created_at.strftime("%d/%m/%Y"),
        "saat": order.created_at.strftime("%H:%M:%S"),
        "paraBirimi": "TRY",
        "faturaTipi": "Satis",
        "vknTckn": "11111111111",  # Test identity number
        "aliciAdi": customer_name,
        "aliciSoyadi": "-",
        "sehir": "Bursa",
        "ulke": "Türkiye",
        "mahalleSemtIlce": "Nilüfer",
        "items": items,
    }

    return invoice_data


def checkout_confirm_view(request):
    order = Order.objects.get(
        id=request.session.get("order_id")
    )

    if request.method == "POST":
        pre_info_ok = request.POST.get("pre_info")
        contract_ok = request.POST.get("distance_contract")

        if not pre_info_ok or not contract_ok:
            messages.error(
                request,
                "Siparişe devam edebilmek için sözleşmeleri onaylamalısınız."
            )
            return redirect("checkout")

        shipping_address = request.POST.get("shipping_address")

        # 🔒 REAL TEXT GENERATED HERE
        order.pre_information_text = generate_pre_information_text(
            order, shipping_address
        )
        order.distance_sales_contract_text = generate_distance_sales_contract(
            order, shipping_address
        )

        order.pre_information_approved = True
        order.distance_contract_approved = True
        order.contracts_approved_at = timezone.now()

        order.save()

        # 💳 PAYMENT PROCESS STARTS HERE
        return redirect("payment_start")

    return render(request, "checkout/confirm.html", {
        "order": order
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_order_contracts(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(
        request,
        "management/admin-order-contracts.html",
        {
            "order": order
        }
    )


# ========== CANCELLATION OPERATIONS ==========

@login_required
def cancel_order(request, order_id):
    """Full order cancellation - Customer and Admin"""
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check
    if not request.user.is_staff and order.user != request.user:
        messages.error(request, "Bu siparişi iptal etme yetkiniz yok.")
        return redirect("home")
    
    # Only orders with "paid" and "preparing" status can be cancelled
    if order.status not in ["paid", "preparing"]:
        messages.error(request, "Sadece 'Ödendi' ve 'Hazırlanıyor' statüsündeki siparişler iptal edilebilir.")
        return redirect("order-tracking" if not request.user.is_staff else "admin-order-list")
    
    if request.method == "POST":
        reason = request.POST.get("cancellation_reason", "")
        
        # Cancel all items
        for item in order.items.all():
            item.cancelled_quantity = item.quantity
            item.save()
        
        # Cancel the order
        order.status = "cancelled"
        order.cancelled_at = timezone.now()
        order.cancelled_by = request.user
        order.cancellation_reason = reason
        order.save()
        
        # If the order is paid, restore the stock
        if order.paid_at:
            from payments.iyzico import restore_order_stock
            try:
                restore_order_stock(order)
            except Exception as e:
                logger.exception("Failed to restore stock in cancel_order: %s", str(e))
        
        messages.success(request, "Sipariş başarıyla iptal edildi.")
        
        if request.user.is_staff:
            return redirect("admin-order-list")
        return redirect("order-tracking")
    
    return render(request, "orders/cancel-order.html", {"order": order})


@login_required
def cancel_order_partial(request, order_id):
    """Advanced partial order cancellation - Cancel by selecting all products"""
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check
    if not request.user.is_staff and order.user != request.user:
        messages.error(request, "Bu siparişi iptal etme yetkiniz yok.")
        return redirect("home")
    
    # Only orders with "paid" and "preparing" status can be cancelled
    if order.status not in ["paid", "preparing"]:
        messages.error(request, "Sadece 'Ödendi' ve 'Hazırlanıyor' statüsündeki siparişler iptal edilebilir.")
        return redirect("order-tracking" if not request.user.is_staff else "admin-order-list")
    
    if request.method == "POST":
        cancellation_reason = request.POST.get("cancellation_reason", "").strip()
        total_cancelled = 0
        cancelled_items = []
        
        # Check the cancellation quantity for each item and cancel
        for item in order.items.all():
            if item.is_fully_cancelled:
                continue  # Already fully cancelled
                
            cancel_quantity_str = request.POST.get(f"cancel_quantity_{item.id}", "0")
            try:
                cancel_quantity = int(cancel_quantity_str)
            except ValueError:
                cancel_quantity = 0
            
            if cancel_quantity > 0:
                available_to_cancel = item.active_quantity
                if cancel_quantity > available_to_cancel:
                    messages.error(request, f"{item.product.name} için en fazla {available_to_cancel} adet iptal edilebilir.")
                    return render(request, "orders/cancel-order-partial.html", {
                        "order": order
                    })
                
                # Cancel
                item.cancelled_quantity += cancel_quantity
                item.save()
                total_cancelled += cancel_quantity
                cancelled_items.append(f"{item.product.name} ({cancel_quantity} adet)")
                
                # If the order is paid, restore the stock for the cancelled quantity
                if order.paid_at:
                    try:
                        # Restore the stock for the cancelled quantity
                        product = item.product
                        from products.models import ProductVariant
                        
                        if product.has_sizes or product.has_colors:
                            filter_kwargs = {'product': product}
                            if product.has_sizes:
                                filter_kwargs['size'] = item.size if item.size else None
                            else:
                                filter_kwargs['size__isnull'] = True
                            if product.has_colors:
                                filter_kwargs['color'] = item.color if item.color else None
                            else:
                                filter_kwargs['color__isnull'] = True
                            
                            variant = ProductVariant.objects.filter(**filter_kwargs).first()
                            if variant:
                                variant.stock += cancel_quantity
                                variant.save(update_fields=['stock'])
                                logger.info("STOCK RESTORED (partial): Variant %s stock restored by %s", variant.id, cancel_quantity)
                        else:
                            product.stock += cancel_quantity
                            product.save(update_fields=['stock'])
                            logger.info("STOCK RESTORED (partial): Product %s stock restored by %s", product.id, cancel_quantity)
                    except Exception as e:
                        logger.exception("Failed to restore stock in cancel_order_partial: %s", str(e))
        
        if total_cancelled == 0:
            messages.warning(request, "Hiçbir ürün seçilmedi.")
            return render(request, "orders/cancel-order-partial.html", {
                "order": order
            })
        
        # If all items are cancelled, cancel the order
        all_cancelled = all(item.is_fully_cancelled for item in order.items.all())
        if all_cancelled:
            order.status = "cancelled"
            order.cancelled_at = timezone.now()
            order.cancelled_by = request.user
            order.cancellation_reason = cancellation_reason or "Tüm ürünler iptal edildi."
            order.save()
            messages.success(request, f"Toplam {total_cancelled} adet ürün iptal edildi. Sipariş tamamen iptal edildi.")
        else:
            # Partial cancellation - update the order status (status remains the same)
            if cancellation_reason:
                # Save the cancellation reason (if there is one)
                if not order.cancellation_reason:
                    order.cancellation_reason = cancellation_reason
                    order.save()
            messages.success(request, f"Toplam {total_cancelled} adet ürün iptal edildi: {', '.join(cancelled_items)}")
        
        if request.user.is_staff:
            return redirect("admin-order-list")
        return redirect("order-tracking")
    
    return render(request, "orders/cancel-order-partial.html", {
        "order": order
    })


@login_required
def cancel_order_item(request, order_id, item_id):
    """Partial order cancellation - Cancel a specific item (Old method - backward compatibility)"""
    order = get_object_or_404(Order, id=order_id)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    # Permission check
    if not request.user.is_staff and order.user != request.user:
        messages.error(request, "Bu siparişi iptal etme yetkiniz yok.")
        return redirect("home")
    
    # Only orders with "paid" and "preparing" status can be cancelled
    if order.status not in ["paid", "preparing"]:
        messages.error(request, "Sadece 'Ödendi' ve 'Hazırlanıyor' statüsündeki siparişler iptal edilebilir.")
        return redirect("order-tracking" if not request.user.is_staff else "admin-order-list")
    
    # Already fully cancelled?
    if order_item.is_fully_cancelled:
        messages.error(request, "Bu ürün zaten tamamen iptal edilmiş.")
        return redirect("order-tracking" if not request.user.is_staff else "admin-order-list")
    
    if request.method == "POST":
        cancel_quantity = int(request.POST.get("cancel_quantity", 0))
        
        if cancel_quantity <= 0:
            messages.error(request, "Geçerli bir miktar giriniz.")
            return render(request, "orders/cancel-order-item.html", {
                "order": order,
                "order_item": order_item
            })
        
        # Check the cancellation quantity
        available_to_cancel = order_item.active_quantity
        if cancel_quantity > available_to_cancel:
            messages.error(request, f"En fazla {available_to_cancel} adet iptal edilebilir.")
            return render(request, "orders/cancel-order-item.html", {
                "order": order,
                "order_item": order_item
            })
        
        # Cancel
        order_item.cancelled_quantity += cancel_quantity
        order_item.save()
        
        # If the order is paid, restore the stock for the cancelled quantity
        if order.paid_at:
            from payments.iyzico import restore_order_stock
            # Restore the stock for the cancelled quantity
            try:
                # Temporarily add only the cancelled quantity of this item
                product = order_item.product
                from products.models import ProductVariant
                
                if product.has_sizes or product.has_colors:
                    filter_kwargs = {'product': product}
                    if product.has_sizes:
                        filter_kwargs['size'] = order_item.size if order_item.size else None
                    else:
                        filter_kwargs['size__isnull'] = True
                    if product.has_colors:
                        filter_kwargs['color'] = order_item.color if order_item.color else None
                    else:
                        filter_kwargs['color__isnull'] = True
                    
                    variant = ProductVariant.objects.filter(**filter_kwargs).first()
                    if variant:
                        variant.stock += cancel_quantity
                        variant.save(update_fields=['stock'])
                        logger.info("STOCK RESTORED (partial): Variant %s stock restored by %s", variant.id, cancel_quantity)
                else:
                    product.stock += cancel_quantity
                    product.save(update_fields=['stock'])
                    logger.info("STOCK RESTORED (partial): Product %s stock restored by %s", product.id, cancel_quantity)
            except Exception as e:
                logger.exception("Failed to restore stock in cancel_order_item: %s", str(e))
        
        # If all items are cancelled, cancel the order
        all_cancelled = all(item.is_fully_cancelled for item in order.items.all())
        if all_cancelled:
            order.status = "cancelled"
            order.cancelled_at = timezone.now()
            order.cancelled_by = request.user
            order.cancellation_reason = "Tüm ürünler iptal edildi."
            order.save()
            messages.success(request, "Tüm ürünler iptal edildiği için sipariş iptal edildi.")
        else:
            messages.success(request, f"{cancel_quantity} adet ürün iptal edildi.")
        
        if request.user.is_staff:
            return redirect("admin-order-list")
        return redirect("order-tracking")
    
    return render(request, "orders/cancel-order-item.html", {
        "order": order,
        "order_item": order_item
    })


# ========== RETURN REQUESTS ==========

@login_required
def create_return_request(request, order_id, item_id):
    """Create a return request"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    # Only orders with "delivered" status can create a return request
    if order.status != "delivered":
        messages.error(request, "Sadece teslim edilmiş siparişler için iade talebi oluşturulabilir.")
        return redirect("order-tracking")
    
    # Check if there is an existing return request
    existing_request = ReturnRequest.objects.filter(
        order=order,
        order_item=order_item,
        status__in=['pending', 'approved']
    ).first()
    
    if existing_request:
        messages.info(request, "Bu ürün için zaten aktif bir iade talebiniz var.")
        return redirect("order-tracking")
    
    if request.method == "POST":
        reason = request.POST.get("reason")
        reason_detail = request.POST.get("reason_detail", "")
        quantity = int(request.POST.get("quantity", 1))
        
        if not reason:
            messages.error(request, "Lütfen iade sebebi seçiniz.")
            return render(request, "orders/create-return-request.html", {
                "order": order,
                "order_item": order_item
            })
        
        if quantity <= 0 or quantity > order_item.quantity:
            messages.error(request, "Geçerli bir miktar giriniz.")
            return render(request, "orders/create-return-request.html", {
                "order": order,
                "order_item": order_item
            })
        
        # Create a return request
        return_request = ReturnRequest.objects.create(
            order=order,
            order_item=order_item,
            user=request.user,
            quantity=quantity,
            reason=reason,
            reason_detail=reason_detail,
            status='pending'
        )
        
        messages.success(request, "İade talebiniz oluşturuldu. İnceleme sonrası size bilgi verilecektir.")
        return redirect("order-tracking")
    
    return render(request, "orders/create-return-request.html", {
        "order": order,
        "order_item": order_item
    })


@login_required
def return_request_list(request):
    """List the user's return requests"""
    return_requests = ReturnRequest.objects.filter(user=request.user).select_related('order', 'order_item__product').order_by('-created_at')
    
    # Get the delivered orders (orders that can create a return request)
    delivered_orders = Order.objects.filter(
        user=request.user,
        status='delivered'
    ).prefetch_related('items__product').order_by('-created_at')
    
    return render(request, "orders/return-request-list.html", {
        "return_requests": return_requests,
        "delivered_orders": delivered_orders
    })


@login_required
def select_order_for_return(request):
    """Select an order for return request"""
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        if not order_id:
            messages.error(request, "Lütfen bir sipariş seçiniz.")
            return redirect('return-request-list')
        
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Only orders with "delivered" status can create a return request
        if order.status != "delivered":
            messages.error(request, "Sadece teslim edilmiş siparişler için iade talebi oluşturulabilir.")
            return redirect('return-request-list')
        
        # Check the items that can be returned in the order
        available_items = []
        for item in order.items.all():
            # Check if the item is already fully returned
            existing_returns = ReturnRequest.objects.filter(
                order=order,
                order_item=item,
                status__in=['pending', 'approved']
            ).aggregate(total_returned=Sum('quantity'))['total_returned'] or 0
            
            if item.quantity > existing_returns:
                available_items.append(item)
        
        if not available_items:
            messages.warning(request, "Bu siparişte iade edilebilecek ürün bulunmamaktadır.")
            return redirect('return-request-list')
        
        # If there is only one item, direct to the return request page
        if len(available_items) == 1:
            return redirect('create-return-request', order_id=order.id, item_id=available_items[0].id)
        
        # If there is more than one item, direct to order-tracking, the user can select from there
        messages.info(request, f"Sipariş #{order.id} seçildi. Lütfen iade etmek istediğiniz ürünü seçiniz.")
        return redirect('order-tracking')
    
    return redirect('return-request-list')


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_return_requests(request):
    """List of active return requests for the admin (pending, approved, received)"""
    return_requests = ReturnRequest.objects.filter(
        status__in=['pending', 'approved', 'received']
    ).select_related('order', 'order_item__product', 'user').order_by('-created_at')
    return render(request, "management/admin-return-requests.html", {
        "return_requests": return_requests
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_return_requests_history(request):
    """List of past return requests for the admin (completed, rejected)"""
    return_requests = ReturnRequest.objects.filter(
        status__in=['completed', 'rejected']
    ).select_related('order', 'order_item__product', 'user', 'processed_by').order_by('-created_at')
    
    # Search filter
    search_query = request.GET.get('q', '').strip()
    if search_query:
        return_requests = return_requests.filter(
            Q(order__id__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(order_item__product__name__icontains=search_query)
        )
    
    return render(request, "management/admin-return-requests-history.html", {
        "return_requests": return_requests,
        "search_query": search_query
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_return_request_detail(request, request_id):
    """Return request detail and processing for the admin"""
    return_request = get_object_or_404(ReturnRequest, id=request_id)
    
    if request.method == "POST":
        action = request.POST.get("action")
        admin_note = request.POST.get("admin_note", "")
        
        if action == "approve":
            return_request.status = "approved"
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            return_request.admin_note = admin_note
            return_request.save()
            messages.success(request, "İade talebi onaylandı ve MNG kodu verilebilir.")
        elif action == "reject":
            return_request.status = "rejected"
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            return_request.admin_note = admin_note
            return_request.save()
            messages.success(request, "İade talebi reddedildi.")
        elif action == "mark_received":
            # Mark the product as received, the status is now "received"
            return_request.status = "received"
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            return_request.admin_note = admin_note
            return_request.save()
            messages.success(request, "Ürün geldi olarak işaretlendi. İnceleme yapabilirsiniz.")
        elif action == "complete":
            # After review, approved
            return_request.status = "completed"
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            return_request.admin_note = admin_note
            return_request.save()
            messages.success(request, "İade işlemi tamamlandı ve para iadesi yapılabilir.")
        elif action == "reject_after_review":
            # After review, rejected
            return_request.status = "rejected"
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            return_request.admin_note = admin_note
            return_request.save()
            messages.success(request, "İade talebi incelendikten sonra reddedildi.")
        
        return redirect("admin-return-requests")
    
    return render(request, "management/admin-return-request-detail.html", {
        "return_request": return_request
    })