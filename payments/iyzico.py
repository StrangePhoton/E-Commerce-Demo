from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import format_html, strip_tags
import json
import logging
import iyzipay

from orders.models import Order, OrderItem
from products.models import ProductVariant
from payments.iyzico_client import IyzicoClient

logger = logging.getLogger(__name__)

def send_order_notification_to_admin(order):
    """
    When order is paid, send notification email to the configured admin address.
    """
    try:
        admin_email = settings.ADMIN_NOTIFICATION_EMAIL
        
        # Customer information
        customer_name = order.user.get_full_name() if order.user else "Misafir Kullanıcı"
        customer_email = order.user.email if order.user else "E-posta yok"
        customer_phone = order.shipping_phone or "Telefon yok"
        
        # Order items
        items_html = ""
        for item in order.items.all():
            # If variant information exists, show it
            variant_info = ""
            if item.size or item.color:
                variant_parts = []
                if item.size:
                    variant_parts.append("Beden: " + str(item.size))
                if item.color:
                    variant_parts.append("Renk: " + str(item.color))
                variant_info = "<br><small style='color: #777;'>(" + ", ".join(variant_parts) + ")</small>"
            
            product_name = str(item.product.name) + variant_info
            items_html += """
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px; text-align: left;">{}</td>
                <td style="padding: 12px; text-align: center;">{}</td>
                <td style="padding: 12px; text-align: right;">{:.2f} ₺</td>
                <td style="padding: 12px; text-align: right;">{:.2f} ₺</td>
            </tr>
            """.format(product_name, item.quantity, float(item.price), float(item.price * item.quantity))
        
        # Invoice information
        invoice_info = ""
        if order.invoice_type:
            # Get the visible name of the invoice type
            invoice_type_choices = {
                'individual': 'Bireysel',
                'corporate': 'Kurumsal',
                'sole_proprietor': 'Şahıs Şirketi'
            }
            invoice_type_display = invoice_type_choices.get(order.invoice_type, order.invoice_type)
            
            # Invoice address information
            billing_address_parts = []
            if order.billing_full_name:
                billing_address_parts.append("<p style='margin: 3px 0;'><strong>{}</strong></p>".format(str(order.billing_full_name)))
            if order.billing_phone:
                billing_address_parts.append("<p style='margin: 3px 0;'>{}</p>".format(str(order.billing_phone)))
            if order.billing_address:
                billing_address_parts.append("<p style='margin: 3px 0;'>{}</p>".format(str(order.billing_address)))
            if order.billing_district and order.billing_city:
                billing_address_parts.append("<p style='margin: 3px 0;'>{} / {}</p>".format(str(order.billing_district), str(order.billing_city).upper()))
            
            billing_address_info = ""
            if billing_address_parts:
                billing_address_info = """
                <div style="margin-top: 15px; padding: 12px; background: #fff; border-left: 3px solid #667eea; border-radius: 4px;">
                    <h4 style="margin: 0 0 8px 0; color: #2c3e50; font-size: 14px;">Fatura Adresi:</h4>
                    {}
                </div>
                """.format("".join(billing_address_parts))
            
            invoice_parts = ["<p style='margin: 5px 0;'><strong>Fatura Tipi:</strong> {}</p>".format(invoice_type_display)]
            if order.tax_number:
                invoice_parts.append("<p style='margin: 5px 0;'><strong>Vergi Numarası:</strong> {}</p>".format(str(order.tax_number)))
            if order.invoice_identity_number:
                invoice_parts.append("<p style='margin: 5px 0;'><strong>TC Kimlik No:</strong> {}</p>".format(str(order.invoice_identity_number)))
            
            invoice_info = """
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 16px;">Fatura Bilgileri</h3>
                {}
                {}
            </div>
            """.format("".join(invoice_parts), billing_address_info)
        
        # HTML email content - use normal string format instead of format_html
        email_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .info-box h3 {{ margin: 0 0 10px 0; color: #2c3e50; font-size: 16px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #667eea; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 12px; }}
                .total {{ font-size: 18px; font-weight: bold; color: #27ae60; text-align: right; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #777; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">Yeni Sipariş Bildirimi</h1>
                    <p style="margin: 10px 0 0 0; font-size: 18px;">Sipariş #{}</p>
                </div>
                <div class="content">
                    <div class="info-box">
                        <h3>Müşteri Bilgileri</h3>
                        <p style="margin: 5px 0;"><strong>Ad Soyad:</strong> {}</p>
                        <p style="margin: 5px 0;"><strong>E-posta:</strong> {}</p>
                        <p style="margin: 5px 0;"><strong>Telefon:</strong> {}</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>Teslimat Adresi</h3>
                        <p style="margin: 5px 0;"><strong>{}</strong></p>
                        <p style="margin: 5px 0;">{}</p>
                        <p style="margin: 5px 0;">{} / {}</p>
                    </div>
                    
                    {}
                    
                    <h3 style="color: #2c3e50; margin-top: 30px;">Sipariş Detayları</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Ürün</th>
                                <th style="text-align: center;">Adet</th>
                                <th style="text-align: right;">Birim Fiyat</th>
                                <th style="text-align: right;">Toplam</th>
                            </tr>
                        </thead>
                        <tbody>
                            {}
                        </tbody>
                    </table>
                    
                    <div class="total">
                        <p style="margin: 5px 0;">Ara Toplam: {:.2f} ₺</p>
                        <p style="margin: 5px 0;">Kargo Ücreti: {:.2f} ₺</p>
                        <p style="margin: 10px 0; font-size: 20px;">Toplam Tutar: {:.2f} ₺</p>
                    </div>
                    
                    <div class="footer">
                        <p>Bu e-posta otomatik olarak gönderilmiştir.</p>
                        <p>{} E-Ticaret Sistemi</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """.format(
            order.id,
            str(customer_name),
            str(customer_email),
            str(customer_phone),
            str(order.shipping_full_name),
            str(order.shipping_address),
            str(order.shipping_district),
            str(order.shipping_city),
            invoice_info,
            items_html,
            float(order.items_total),
            float(order.cargo_price),
            float(order.total_price),
            settings.STORE_NAME,
        )
        
        # Create email
        email = EmailMultiAlternatives(
            subject="Yeni Sipariş Bildirimi - Sipariş #{}".format(order.id),
            body=strip_tags(email_html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[admin_email]
        )
        email.attach_alternative(email_html, "text/html")
        
        email.send()
        logger.info("ADMIN NOTIFICATION EMAIL SENT: Order %s notification sent to %s", order.id, admin_email)
        
    except Exception as e:
        logger.exception("ADMIN NOTIFICATION EMAIL ERROR: Failed to send notification email for order %s: %s", order.id, str(e))

def reduce_order_stock(order):
    """
    When order is paid, reduce the stock.
    For each OrderItem:
    - If variant exists (size/color), reduce the variant stock
    - If variant does not exist, reduce the product stock
    - Only reduce the active quantity (quantity - cancelled_quantity)
    """
    try:
        for item in order.items.all():
            # Consider the cancelled quantity - only reduce the active quantity
            active_quantity = item.active_quantity
            
            if active_quantity <= 0:
                continue  # For cancelled products, reduce the stock
            
            product = item.product
            
            # Variant check
            if product.has_sizes or product.has_colors:
                # If variant exists, find the relevant variant and reduce the stock
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
                    if variant.stock >= active_quantity:
                        variant.stock -= active_quantity
                        variant.save(update_fields=['stock'])
                        logger.info("STOCK REDUCED: Variant %s (size=%s, color=%s) stock reduced by %s, new stock: %s", 
                                  variant.id, item.size, item.color, active_quantity, variant.stock)
                    else:
                        logger.warning("STOCK INSUFFICIENT: Variant %s has only %s stock, trying to reduce %s", 
                                     variant.id, variant.stock, active_quantity)
                        variant.stock = 0  # Negative stock is not allowed
                        variant.save(update_fields=['stock'])
                else:
                    logger.warning("STOCK REDUCE FAILED: Variant not found for product %s (size=%s, color=%s)", 
                                 product.id, item.size, item.color)
            else:
                # If variant does not exist, reduce the product stock
                if product.stock >= active_quantity:
                    product.stock -= active_quantity
                    product.save(update_fields=['stock'])
                    logger.info("STOCK REDUCED: Product %s stock reduced by %s, new stock: %s", 
                              product.id, active_quantity, product.stock)
                else:
                    logger.warning("STOCK INSUFFICIENT: Product %s has only %s stock, trying to reduce %s", 
                                 product.id, product.stock, active_quantity)
                    product.stock = 0  # Negative stock is not allowed
                    product.save(update_fields=['stock'])
        
        logger.info("STOCK REDUCTION COMPLETE: Order %s stock reduced successfully", order.id)
    except Exception as e:
        logger.exception("STOCK REDUCTION ERROR: Failed to reduce stock for order %s: %s", order.id, str(e))


def restore_order_stock(order):
    """
    When order is cancelled, restore the stock.
    For each OrderItem:
    - If variant exists (size/color), restore the variant stock
    - If variant does not exist, restore the product stock
    - Only restore the active quantity (quantity - cancelled_quantity)
    """
    try:
        for item in order.items.all():
            # Consider the cancelled quantity - only restore the active quantity
            active_quantity = item.active_quantity
            
            if active_quantity <= 0:
                continue  # For cancelled products, restore the stock
            
            product = item.product
            
            # Variant check
            if product.has_sizes or product.has_colors:
                # If variant exists, find the relevant variant and restore the stock
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
                    variant.stock += active_quantity
                    variant.save(update_fields=['stock'])
                    logger.info("STOCK RESTORED: Variant %s (size=%s, color=%s) stock restored by %s, new stock: %s", 
                              variant.id, item.size, item.color, active_quantity, variant.stock)
                else:
                    logger.warning("STOCK RESTORE FAILED: Variant not found for product %s (size=%s, color=%s)", 
                                 product.id, item.size, item.color)
            else:
                # If variant does not exist, restore the product stock
                product.stock += active_quantity
                product.save(update_fields=['stock'])
                logger.info("STOCK RESTORED: Product %s stock restored by %s, new stock: %s", 
                          product.id, active_quantity, product.stock)
        
        logger.info("STOCK RESTORATION COMPLETE: Order %s stock restored successfully", order.id)
    except Exception as e:
        logger.exception("STOCK RESTORATION ERROR: Failed to restore stock for order %s: %s", order.id, str(e))

@login_required
def iyzico_init(request, order_id):
    if request.method != "POST":
        return redirect("checkout-payment")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    selected_method = request.POST.get("payment_method")
    if selected_method != "iyzico":
        messages.error(request, "Bu ödeme yöntemi şu anda desteklenmiyor.")
        return redirect("checkout-payment")

    if order.status not in ["awaiting_payment", "awaiting_contracts"]:
        messages.error(request, "Geçersiz ödeme durumu.")
        return redirect("checkout-payment")

    card_holder = request.POST.get("card_holder")
    card_number = request.POST.get("card_number", "").replace(" ", "")
    expire_month = request.POST.get("card_month")
    expire_year = request.POST.get("card_year")
    cvc = request.POST.get("card_cvc")

    required_fields = [card_holder, card_number, expire_month, expire_year, cvc]
    if not all(required_fields):
        messages.error(request, "Lütfen kart bilgilerinizi eksiksiz doldurun.")
        return redirect("checkout-payment")

    # Simple length check for card number and expiry date
    if len(card_number) < 12 or len(cvc) < 3:
        messages.error(request, "Kart bilgileriniz hatalı görünüyor.")
        return redirect("checkout-payment")

    order.payment_method = "iyzico"
    order.status = "awaiting_payment"
    order.save(update_fields=["payment_method", "status"])

    order.calculate_totals()

    client = IyzicoClient()
    card = {
        "card_holder": card_holder,
        "card_number": card_number,
        "card_month": expire_month,
        "card_year": expire_year,
        "expire_month": expire_month,
        "expire_year": expire_year,
        "cvc": cvc,
    }

    result = client.init_three_ds_payment(order, card, request)

    if result.get("status") != "success":
        messages.error(request, result.get("errorMessage") or "Ödeme başlatılamadı.")
        return redirect("checkout-payment")

    html_content = client.decode_three_ds_html(result["threeDSHtmlContent"])
    return render(
        request,
        "checkout/iyzico-redirect.html",
        {
            "html_content": html_content,
            "order": order,
        },
    )

@csrf_exempt
def iyzico_callback(request):
    # GET ve POST parametrelerini birleştir
    params = {}
    if request.method == "POST":
        params = request.POST.dict()
    elif request.method == "GET":
        params = request.GET.dict()
    else:
        return HttpResponse(status=405)

    logger.info("IYZICO CALLBACK [%s]: %s", request.method, params)

    conversation_id = params.get("conversationId")
    payment_id = params.get("paymentId")
    conversation_data = params.get("conversationData", "").strip()  # Boş string olabilir
    status = params.get("status")
    md_status = params.get("mdStatus")  # 3D Secure status: '1' = success, '0' = failed

    # Critical parameters check
    if not conversation_id:
        logger.warning("IYZICO CALLBACK: conversationId eksik")
        return HttpResponse("error: conversationId required", status=400)

    try:
        order = Order.objects.get(id=conversation_id)
    except Order.DoesNotExist:
        logger.error("IYZICO CALLBACK: Order bulunamadı: %s", conversation_id)
        return HttpResponse("error: order not found", status=404)

    # Session lost, get user from order and automatically login
    # This prevents session loss after bank redirect
    if not request.user.is_authenticated and order.user:
        # Login without specifying backend (use Django's default backend)
        login(request, order.user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info("IYZICO CALLBACK: Session kaybolmuş, user otomatik login yapıldı: %s", order.user.email)

    client = IyzicoClient()

    # If status is failed, return error directly
    if status and status.lower() not in ["success", "1"]:
        logger.warning("IYZICO CALLBACK: 3D Secure başarısız, status: %s", status)
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        request.session["iyzico_success_order"] = order.id
        return redirect("iyzico-error")

    # mdStatus check: '0' is 3D Secure failed
    if md_status == "0":
        logger.warning("IYZICO CALLBACK: 3D Secure başarısız, mdStatus: %s", md_status)
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        request.session["iyzico_success_order"] = order.id
        return redirect("iyzico-error")

    # Payment cannot be completed without payment_id
    if not payment_id:
        logger.warning("IYZICO CALLBACK: paymentId eksik")
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        request.session["iyzico_success_order"] = order.id
        return redirect("iyzico-error")

    # Payment can be completed even if conversation_data is empty (mdStatus and status check is enough)
    # However, Iyzico API expects conversation_data, so send an empty string
    if not conversation_data:
        logger.info("IYZICO CALLBACK: conversationData is empty, continue with mdStatus and status check")
        # If mdStatus is '1' and status is 'success', payment can be accepted
        if md_status == "1" and status and status.lower() == "success":
            logger.info("IYZICO CALLBACK: mdStatus=1 and status=success, payment can be accepted")
            # We can query the payment even without conversation_data
            # But first try ThreedsPayment call with empty conversation_data
            conversation_data = ""  # Send empty string

    # Complete 3D Secure payment
    try:
        payment_result = client.complete_three_ds_payment(
            order_id=conversation_id,
            payment_id=payment_id,
            conversation_data=conversation_data,
        )

        logger.info("IYZICO COMPLETE RESULT: %s", payment_result)

        # Check if payment is successful
        # In Iyzico ThreedsPayment response, paymentStatus does not exist, only status and mdStatus exist
        result_status = payment_result.get("status")
        result_md_status = payment_result.get("mdStatus")
        payment_status = payment_result.get("paymentStatus")  # Bazı durumlarda olabilir
        
        # If successful response from API
        # status="success" and (mdStatus=1 or paymentStatus="SUCCESS")
        is_success = (
            result_status == "success" and 
            (result_md_status == 1 or payment_status == "SUCCESS")
        )
        
        if is_success:
            order.status = "paid"
            order.payment_reference = payment_result.get("paymentId") or payment_id
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "payment_reference", "paid_at"])
            
            # Reduce stock
            reduce_order_stock(order)
            
            # Send notification email to admin
            send_order_notification_to_admin(order)
            
            # Write order_id to session (for success page)
            request.session["iyzico_success_order"] = order.id
            request.session["checkout_order_id"] = order.id
            request.session.modified = True  # Force save session
            request.session.save()  # Save session
            
            # Clear cart
            from cart.models import CartItem
            if order.user:
                CartItem.objects.filter(cart__user=order.user).delete()
            
            logger.info("IYZICO PAYMENT SUCCESS: Order %s paid", order.id)
            # Pass order ID as URL parameter (even if session is lost)
            return redirect("iyzico-success", order_id=order.id)
        
        # If API returns error but mdStatus=1 and status=success, accept payment
        if md_status == "1" and status and status.lower() == "success":
            logger.info("IYZICO CALLBACK: API error but mdStatus=1, payment can be accepted")
            order.status = "paid"
            order.payment_reference = payment_id
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "payment_reference", "paid_at"])
            
            # Reduce stock
            reduce_order_stock(order)
            
            # Send notification email to admin
            send_order_notification_to_admin(order)
            
            request.session["iyzico_success_order"] = order.id
            request.session["checkout_order_id"] = order.id
            request.session.modified = True  # Force save session
            request.session.save()  # Save session
            
            from cart.models import CartItem
            if order.user:
                CartItem.objects.filter(cart__user=order.user).delete()
            
            logger.info("IYZICO PAYMENT SUCCESS (mdStatus): Order %s paid", order.id)
            # Pass order ID as URL parameter (even if session is lost)
            return redirect("iyzico-success", order_id=order.id)
        
        # Failed payment
        error_msg = payment_result.get("errorMessage") or payment_result.get("errorMessage", "Ödeme başarısız oldu")
        logger.error("IYZICO PAYMENT FAILED: %s", error_msg)
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        request.session["iyzico_success_order"] = order.id
        return redirect("iyzico-error")
    
    except Exception as e:
        logger.exception("IYZICO CALLBACK EXCEPTION")
        # Check mdStatus in case of exception
        if md_status == "1" and status and status.lower() == "success":
            logger.info("IYZICO CALLBACK: Exception but mdStatus=1, payment can be accepted")
            order.status = "paid"
            order.payment_reference = payment_id
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "payment_reference", "paid_at"])
            
            # Reduce stock
            reduce_order_stock(order)
            
            # Send notification email to admin
            send_order_notification_to_admin(order)
            
            request.session["iyzico_success_order"] = order.id
            request.session["checkout_order_id"] = order.id
            request.session.modified = True  # Force save session
            request.session.save()  # Save session
            
            from cart.models import CartItem
            if order.user:
                CartItem.objects.filter(cart__user=order.user).delete()
            
            # Pass order ID as URL parameter (even if session is lost)
            return redirect("iyzico-success", order_id=order.id)
        
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        request.session["iyzico_success_order"] = order.id
        return redirect("iyzico-error")

@csrf_exempt
def iyzico_webhook(request):
    try:
        payload = json.loads(request.body.decode())
        logger.info("IYZICO WEBHOOK: %s", payload)
    except json.JSONDecodeError:
        logger.error("IYZICO WEBHOOK: Invalid JSON")
        return HttpResponse("invalid json", status=400)

    # Iyzico webhook can use both conversationId and paymentConversationId
    conversation_id = payload.get("conversationId") or payload.get("paymentConversationId")
    payment_status = payload.get("status") or payload.get("paymentStatus")
    payment_id = payload.get("paymentId") or payload.get("iyziPaymentId")

    if not conversation_id:
        logger.warning("IYZICO WEBHOOK: conversationId eksik")
        return HttpResponse("conversationId required", status=400)

    try:
        order = Order.objects.get(id=conversation_id)
    except Order.DoesNotExist:
        logger.error("IYZICO WEBHOOK: Order bulunamadı: %s", conversation_id)
        return HttpResponse("order not found", status=404)

    if order.status == "paid":
        logger.info("IYZICO WEBHOOK: Order %s zaten ödendi", order.id)
        return HttpResponse("already processed", status=200)

    # Check the status values received in the webhook
    if payment_status in ["SUCCESS", "CALLBACK_THREEDS"]:
        # If payment_status is CALLBACK_THREEDS, payment may not be completed yet, only log
        if payment_status == "CALLBACK_THREEDS":
            logger.info("IYZICO WEBHOOK: 3D Secure callback alındı, order: %s", order.id)
            return HttpResponse("ok", status=200)
        
        # If payment_status is SUCCESS, accept payment
        order.status = "paid"
        order.payment_reference = str(payment_id) if payment_id else None
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "payment_reference", "paid_at"])
        
        # Reduce stock
        reduce_order_stock(order)
        
        # Send notification email to admin
        send_order_notification_to_admin(order)
        
        # Clear cart
        from cart.models import CartItem
        if order.user:
            CartItem.objects.filter(cart__user=order.user).delete()
        
        logger.info("IYZICO WEBHOOK: Order %s paid", order.id)
    else:
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        logger.warning("IYZICO WEBHOOK: Order %s payment failed, status: %s", order.id, payment_status)

    return HttpResponse("ok", status=200)


def iyzico_success(request, order_id):
    """
    Iyzico payment success page.
    Order ID is passed as URL parameter, so it works even if session is lost.
    """
    # First check URL parameter, then session
    if not order_id:
        order_id = request.session.pop("iyzico_success_order", None)
        if not order_id:
            messages.error(request, "Sipariş bulunamadı.")
            return redirect("checkout-payment")
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Sipariş bulunamadı.")
        return redirect("checkout-payment")
    
    # Session lost, get user from order and automatically login
    # This prevents session loss after bank redirect
    if not request.user.is_authenticated and order.user:
        # Login without specifying backend (use Django's default backend)
        login(request, order.user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info("IYZICO SUCCESS: Session lost, user automatically logged in: %s", order.user.email)
    
    # User check - if user is authenticated and order is not for them, show error
    if request.user.is_authenticated:
        if order.user and order.user != request.user:
            messages.error(request, "This order is not for you.")
            return redirect("home")
    
    # Payment status check
    if order.status != "paid":
        messages.error(request, "Payment is not completed yet.")
        return redirect("iyzico-error")
    
    # Clear order_id from session (now coming from URL)
    request.session.pop("iyzico_success_order", None)
    
    return render(request, "checkout/iyzico-success.html", {"order": order})


def iyzico_error(request):
    order_id = request.session.get("iyzico_success_order")
    order = None
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            pass
    
    return render(request, "checkout/payment-error.html", {
        "order": order,
        "message": "Ödeme işlemi tamamlanamadı. Lütfen tekrar deneyin veya farklı bir kart deneyin."
    })
