# orders/gib_client.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from xhtml2pdf import pisa
from django.core.mail import EmailMessage
from django.conf import settings
import os

class GibClient:
    def __init__(self, username=None, password=None, test_mode=True):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.token = None
        self.test_mode = test_mode
        self.base_url = (
            "https://earsivportaltest.efatura.gov.tr" if test_mode else "https://earsivportal.efatura.gov.tr"
        )

    def login(self):
        login_url = f"{self.base_url}/intragiris.jsp"
        payload = {"userid": self.username, "sifre": self.password}
        response = self.session.post(login_url, data=payload)
        if response.ok:
            self.token = self._extract_token(response.text)
            return self.token
        raise Exception("Login failed")

    def _extract_token(self, html):
        soup = BeautifulSoup(html, "html.parser")
        token_tag = soup.find("input", {"name": "token"})
        return token_tag.get("value") if token_tag else None

    def logout(self):
        logout_url = f"{self.base_url}/logout.jsp"
        self.session.get(logout_url)
        self.token = None

    def create_invoice(self, invoice_data: dict):
        create_url = f"{self.base_url}/earsiv-services/dispatch"
        headers = {"Content-Type": "application/json"}
        response = self.session.post(create_url, json=invoice_data, headers=headers)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Invoice creation failed: {response.status_code} {response.text}")

    def get_invoice_html(self, uuid: str):
        url = f"{self.base_url}/earsiv-services/download-html?uuid={uuid}"
        response = self.session.get(url)
        if response.ok:
            return response.text
        raise Exception("Failed to retrieve invoice HTML")

    def get_document(self, uuid: str):
        url = f"{self.base_url}/earsiv-services/get-document?uuid={uuid}"
        response = self.session.get(url)
        if response.ok:
            return response.json()
        raise Exception("Failed to get document")

    def send_invoice_email(self, order, html_content):
        pdf_path = f"/tmp/invoice_{order.id}.pdf"
        with open(pdf_path, "w+b") as pdf_file:
            pisa.CreatePDF(html_content, dest=pdf_file)

        to_email = order.user.email if order.user else order.guest_email
        if not to_email:
            raise ValueError("Geçerli bir e-posta adresi bulunamadı.")

        email = EmailMessage(
            subject=f"{settings.STORE_NAME} E-Faturanız (Demo)",
            body="Siparişinize ait e-fatura ektedir.",
            to=[to_email]
        )
        with open(pdf_path, "rb") as f:
            email.attach(f"invoice_{order.id}.pdf", f.read(), "application/pdf")
        email.send()

        os.remove(pdf_path)
