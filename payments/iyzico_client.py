import base64
from decimal import Decimal
import json
import logging
from typing import Dict, Any, List

import iyzipay
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


class IyzicoClient:
    def __init__(self) -> None:
        self.options = {
            "api_key": settings.IYZICO_API_KEY.strip(),
            "secret_key": settings.IYZICO_SECRET_KEY.strip(),
            "base_url": settings.IYZICO_BASE_URL.strip(),
        }

    def _build_buyer(self, order, request) -> Dict[str, Any]:
        user = order.user
        return {
            "id": str(user.id) if user and user.id else "guest",
            "name": getattr(user, "first_name", "") or "Musteri",
            "surname": getattr(user, "last_name", "") or "Soyad",
            "email": getattr(user, "email", "") or "guest@example.com",
            "identityNumber": "11111111111",
            "registrationAddress": order.shipping_address,
            "ip": request.META.get("REMOTE_ADDR", "127.0.0.1"),
            "city": order.shipping_city or "Bursa",
            "country": order.shipping_country or "Turkey",
        }

    def _build_address(self, order) -> Dict[str, Any]:
        return {
            "contactName": order.shipping_full_name or "Musteri",
            "city": order.shipping_city or "Bursa",
            "country": order.shipping_country or "Turkey",
            "address": order.shipping_address,
        }

    def _build_basket_items(self, order) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        # PRODUCTS
        for item in order.items.all():
            items.append(
                {
                    "id": str(item.product.id),
                    "name": item.product.name,
                    "category1": "Medikal",
                    "itemType": "PHYSICAL",
                    "price": str((item.price * item.quantity).quantize(Decimal("0.01"))),
                }
            )

        # CARGO (VERY IMPORTANT)
        if order.cargo_price > 0:
            items.append(
                {
                    "id": "CARGO",
                    "name": "Kargo Ücreti",
                    "category1": "Hizmet",
                    "itemType": "VIRTUAL",
                    "price": str(order.cargo_price.quantize(Decimal("0.01"))),
                }
            )

        return items

    def init_three_ds_payment(self, order, card: Dict[str, str], request) -> Dict[str, Any]:
        logger.error("IYZICO OPTIONS → %s", self.options)
        callback_url = settings.IYZICO_CALLBACK_URL
        success_url = settings.IYZICO_SUCCESS_URL
        error_url = settings.IYZICO_ERROR_URL

        request_data = {
            "locale": "tr",
            "conversationId": str(order.id),
            "price": str(order.total_price.quantize(Decimal("0.01"))),
            "paidPrice": str(order.total_price.quantize(Decimal("0.01"))),
            "currency": "TRY",
            "installment": "1",
            "paymentChannel": "WEB",
            "paymentGroup": "PRODUCT",
            "callbackUrl": callback_url,
            "buyer": self._build_buyer(order, request),
            "shippingAddress": self._build_address(order),
            "billingAddress": self._build_address(order),
            "basketItems": self._build_basket_items(order),
            "paymentCard": {
                "cardHolderName": card["card_holder"],
                "cardNumber": card["card_number"],
                "expireMonth": card["expire_month"],
                "expireYear": card["expire_year"],
                "cvc": card["cvc"],
                "registerCard": "0",
            },
        }

        try:
            response = iyzipay.ThreedsInitialize().create(
                request_data,
                self.options,
            )

            raw = response.read().decode("utf-8")
            logger.error("IYZICO INIT RAW RESPONSE: %s", raw)

            return json.loads(raw)

        except Exception as e:
            logger.exception("IYZICO INIT EXCEPTION")
            return {
                "status": "failure",
                "errorMessage": str(e),
            }

    def decode_three_ds_html(self, html_content: str) -> str:
        return base64.b64decode(html_content).decode("utf-8")

    def complete_three_ds_payment(
        self,
        order_id: str,
        payment_id: str,
        conversation_data: str,
    ) -> Dict[str, Any]:

        request_data = {
            "locale": "tr",
            "conversationId": str(order_id),
            "paymentId": payment_id,
            "conversationData": conversation_data,
        }

        try:
            response = iyzipay.ThreedsPayment().create(
                request_data,
                self.options,
            )

            raw = response.read().decode("utf-8")
            logger.error("IYZICO COMPLETE RAW RESPONSE: %s", raw)

            return json.loads(raw)

        except Exception as e:
            logger.exception("IYZICO COMPLETE EXCEPTION")
            return {
                "status": "failure",
                "errorMessage": str(e),
            }
