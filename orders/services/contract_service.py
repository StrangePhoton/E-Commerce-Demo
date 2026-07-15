from django.utils import timezone
from orders.contracts import (
    generate_pre_information_text,
    generate_distance_sales_contract
)

class ContractService:

    @staticmethod
    def create_and_attach_contracts(order, shipping_address):
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
