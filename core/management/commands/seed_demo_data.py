from __future__ import annotations

import io
import os
import random
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image


DEMO_MARKER = "[DEMO DATA]"
DEMO_SLIDE_PREFIX = "[DEMO SLIDE]"
DEMO_CONTACT_PREFIX = "[DEMO İLETİŞİM]"

TARGET_CATEGORIES = 7
TARGET_PRODUCTS = 65
TARGET_USERS = 2
TARGET_ADDRESSES = 6
TARGET_ORDERS = 18
TARGET_ORDER_ITEMS = 40
TARGET_FAVORITES = 12
TARGET_RATINGS = 35
TARGET_REVIEWS = 18
TARGET_CAMPAIGNS = 4
TARGET_SLIDES = 3
TARGET_MESSAGES = 6
TARGET_RETURNS = 3

CATEGORY_NAMES = [
    "Hasta Bakım Malzemeleri",
    "Medikal Sarf Malzemeleri",
    "Medikal Malzemeler",
    "Kişisel Yaşam Malzemeleri",
    "Vitamin & Takviye",
    "Ev ve Yaşam",
    "Elektronik Cihazlar",
]

CATEGORY_PRODUCT_TARGETS = [10, 10, 10, 9, 9, 9, 8]

CATEGORY_PRODUCT_BASES: dict[str, list[tuple[str, Decimal, int]]] = {
    "Hasta Bakım Malzemeleri": [
        ("Ayarlanabilir Hasta Yastığı", Decimal("899.90"), 24),
        ("Dijital Ateş Ölçer", Decimal("249.90"), 40),
        ("Hasta Alt Bezi", Decimal("189.90"), 80),
        ("Yatak Koruyucu Örtü", Decimal("129.90"), 55),
        ("Pulse Oksimetre", Decimal("459.90"), 30),
    ],
    "Medikal Sarf Malzemeleri": [
        ("Steril Gazlı Bez", Decimal("89.90"), 120),
        ("Nitril Muayene Eldiveni", Decimal("219.90"), 75),
        ("Cerrahi Maske Kutusu", Decimal("149.90"), 90),
        ("Antiseptik Solüsyon", Decimal("79.90"), 60),
        ("Tek Kullanımlık Önlük", Decimal("99.90"), 100),
    ],
    "Medikal Malzemeler": [
        ("Dijital Tansiyon Ölçer", Decimal("1299.90"), 18),
        ("Ortopedik Bel Desteği", Decimal("549.90"), 31),
        ("Dizlik Destek Aparatı", Decimal("399.90"), 28),
        ("Bileklik Ateli", Decimal("279.90"), 35),
        ("Nebulizatör Maske Seti", Decimal("159.90"), 42),
    ],
    "Kişisel Yaşam Malzemeleri": [
        ("Ergonomik Boyun Yastığı", Decimal("699.90"), 22),
        ("Günlük İlaç Düzenleyici", Decimal("159.90"), 50),
        ("Ayak Masaj Aleti", Decimal("329.90"), 26),
        ("Banyo Güvenlik Bariyeri", Decimal("449.90"), 19),
        ("Kişisel Bakım Seti", Decimal("259.90"), 33),
    ],
    "Vitamin & Takviye": [
        ("Multivitamin Kompleksi", Decimal("429.90"), 36),
        ("Vitamin C Tablet", Decimal("279.90"), 44),
        ("Omega 3 Kapsül", Decimal("389.90"), 38),
        ("Magnezyum Takviyesi", Decimal("319.90"), 41),
        ("Çinko Tablet", Decimal("199.90"), 47),
    ],
    "Ev ve Yaşam": [
        ("Dijital Mutfak Tartısı", Decimal("379.90"), 27),
        ("Hava Nemlendirici", Decimal("849.90"), 15),
        ("UV Sterilizasyon Lambası", Decimal("599.90"), 21),
        ("Akıllı Termostat", Decimal("729.90"), 17),
        ("Hava Temizleyici Filtre", Decimal("289.90"), 29),
    ],
    "Elektronik Cihazlar": [
        ("Akıllı Vücut Tartısı", Decimal("1099.90"), 20),
        ("Taşınabilir Nebulizatör", Decimal("1399.90"), 12),
        ("Bluetooth Tansiyon Cihazı", Decimal("1199.90"), 14),
        ("Dijital Şeker Ölçüm Cihazı", Decimal("899.90"), 16),
        ("Infrared Termometre", Decimal("349.90"), 25),
    ],
}

PRODUCT_VARIANT_SUFFIXES = [
    "",
    " Plus",
    " Pro",
    " Mini",
    " Set",
    " Paket",
    " Deluxe",
    " Eco",
    " Kompakt",
    " Premium",
]

REVIEW_TEXTS = [
    "Ürün beklentilerimi karşıladı, hızlı kargo için teşekkürler.",
    "Kaliteli malzeme, paketleme özenliydi.",
    "Fiyat performans açısından memnun kaldım.",
    "Kullanımı kolay, ailem için ideal.",
    "Tavsiye ederim, tekrar sipariş vereceğim.",
    "Ürün açıklamasıyla birebir uyumlu.",
    "Müşteri hizmetleri çok ilgiliydi.",
    "Sağlık ürünleri için güvenilir bir mağaza.",
    "Teslimat süresi kısa, ürün sorunsuz geldi.",
    "Boyut ve ölçüler tam istediğim gibiydi.",
    "Uzun süredir kullanıyorum, memnunum.",
    "Hediye olarak aldım, çok beğenildi.",
    "Kurulumu basit, kullanım kılavuzu yeterli.",
    "Stok durumu güncel, sipariş sorunsuz tamamlandı.",
    "İade süreci olmadan sorunsuz bir alışveriş oldu.",
    "Ürün kalitesi fiyatına göre oldukça iyi.",
    "Evde bakım için pratik bir çözüm.",
    "Tekrar alışveriş yapmayı düşünüyorum.",
]

CONTACT_MESSAGES = [
    (
        "Demo Müşteri 1",
        "demo.customer1@example.com",
        "5550000101",
        "Toplu sipariş fiyat teklifi",
        "Kliniğimiz için 50 adet tansiyon ölçer almak istiyoruz. Toplu alım indirimi var mı?",
    ),
    (
        "Demo Müşteri 2",
        "demo.customer2@example.com",
        "5550000102",
        "Kargo takibi",
        "Siparişim kargoya verildi görünüyor ancak takip numarası e-posta ile gelmedi.",
    ),
    (
        "Demo Müşteri 3",
        "demo.customer3@example.com",
        "5550000103",
        "Ürün önerisi",
        "Evde hasta bakımı için hangi yastık modelini önerirsiniz?",
    ),
    (
        "Demo Müşteri 4",
        "demo.customer4@example.com",
        "5550000104",
        "Fatura talebi",
        "Kurumsal fatura kesilmesi için vergi numaramı paylaşmak istiyorum.",
    ),
    (
        "Demo Müşteri 5",
        "demo.customer5@example.com",
        "5550000105",
        "İade süreci",
        "İade talebim onaylandı mı? Kargo kodunu nereden alabilirim?",
    ),
    (
        "Demo Müşteri 6",
        "demo.customer6@example.com",
        "5550000106",
        "Stok bilgisi",
        "Nebulizatör ne zaman tekrar stoklara girecek?",
    ),
]

SLIDE_TITLES = [
    "Yeni Sezon Medikal Ürünler",
    "Ücretsiz Kargo Fırsatı",
    "Vitamin & Takviye İndirimleri",
]

SLIDE_FALLBACK_COLORS = [
    (41, 98, 168),
    (34, 139, 84),
    (192, 86, 43),
]

ORDER_STATUS_PLAN = [
    "delivered",
    "delivered",
    "delivered",
    "delivered",
    "delivered",
    "delivered",
    "delivered",
    "delivered",
    "shipped",
    "shipped",
    "shipped",
    "shipped",
    "preparing",
    "preparing",
    "paid",
    "paid",
    "cancelled",
    "payment_failed",
]

ORDER_ITEM_COUNTS = [3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]


@dataclass
class DemoStoreStats:
    categories: int = 0
    products: int = 0
    users: int = 0
    addresses: int = 0
    orders: int = 0
    order_items: int = 0
    favorites: int = 0
    ratings: int = 0
    reviews: int = 0
    campaigns: int = 0
    slides: int = 0
    messages: int = 0
    returns: int = 0
    admin_username: str = ""
    customer_username: str = ""


def model_field_names(model: type[Any]) -> set[str]:
    return {
        field.name
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False)
    }


def build_demo_product_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []

    for category_name, target_count in zip(
        CATEGORY_NAMES,
        CATEGORY_PRODUCT_TARGETS,
        strict=True,
    ):
        bases = CATEGORY_PRODUCT_BASES[category_name]
        for index in range(target_count):
            base_name, base_price, base_stock = bases[index % len(bases)]
            suffix = PRODUCT_VARIANT_SUFFIXES[index // len(bases)]
            name = f"{base_name}{suffix}"
            price_offset = Decimal(str((index % 5) * 10))
            stock_offset = index % 7

            catalog.append(
                {
                    "name": name,
                    "category": category_name,
                    "description": (
                        f"{DEMO_MARKER} {settings.STORE_NAME} demo mağazası için hazırlanmış "
                        f"{category_name.lower()} ürünüdür."
                    ),
                    "price": (base_price + price_offset).quantize(Decimal("0.01")),
                    "stock": max(base_stock - stock_offset, 5),
                }
            )

    return catalog


DEMO_PRODUCTS = build_demo_product_catalog()


class Command(BaseCommand):
    help = (
        "Create a full demo store simulation with "
        "categories, products, users, orders, and storefront content."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all demo store data before reseeding.",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        self._rng = random.Random(42)
        self.stats = DemoStoreStats()

        if options["reset"]:
            self._delete_demo_store()

        categories = self._seed_categories()
        products = self._seed_products(categories)
        self._seed_product_images(products)
        admin_user, demo_user = self._seed_demo_users()
        addresses = self._seed_addresses(demo_user)
        orders, order_items = self._seed_orders(
            demo_user=demo_user,
            products=products,
            addresses=addresses,
        )
        favorites = self._seed_favorites(demo_user=demo_user, products=products)
        ratings, reviews = self._seed_ratings(
            demo_user=demo_user,
            admin_user=admin_user,
            products=products,
        )
        campaigns = self._seed_campaigns(products)
        slides = self._seed_slides()
        messages = self._seed_contact_messages()
        returns = self._seed_return_requests(
            demo_user=demo_user,
            orders=orders,
        )

        self._seed_site_configuration()
        self._seed_order_settings()

        self.stats.categories = len(categories)
        self.stats.products = len(products)
        self.stats.users = 2
        self.stats.addresses = len(addresses)
        self.stats.orders = len(orders)
        self.stats.order_items = order_items
        self.stats.favorites = favorites
        self.stats.ratings = ratings
        self.stats.reviews = reviews
        self.stats.campaigns = campaigns
        self.stats.slides = slides
        self.stats.messages = messages
        self.stats.returns = returns
        self.stats.admin_username = admin_user.username
        self.stats.customer_username = demo_user.username

        self._print_summary()

    def _delete_demo_store(self) -> None:
        User = get_user_model()
        Product = apps.get_model("products", "Product")
        Category = apps.get_model("products", "Category")
        BulkDiscount = apps.get_model("products", "BulkDiscount")
        ProductRating = apps.get_model("products", "ProductRating")
        Order = apps.get_model("orders", "Order")
        ReturnRequest = apps.get_model("orders", "ReturnRequest")
        Address = apps.get_model("users", "Address")
        Favorite = apps.get_model("users", "Favorite")
        ContactMessage = apps.get_model("users", "ContactMessage")
        HomeSlide = apps.get_model("pages", "HomeSlide")

        demo_users = User.objects.filter(
            username__in=self._demo_usernames(),
        )
        demo_products = Product.objects.filter(
            description__startswith=DEMO_MARKER,
        )
        demo_orders = Order.objects.filter(user__in=demo_users)

        ReturnRequest.objects.filter(user__in=demo_users).delete()
        Order.objects.filter(user__in=demo_users).delete()
        Favorite.objects.filter(user__in=demo_users).delete()
        ProductRating.objects.filter(user__in=demo_users).delete()
        BulkDiscount.objects.filter(product__in=demo_products).delete()
        ContactMessage.objects.filter(subject__startswith=DEMO_CONTACT_PREFIX).delete()
        HomeSlide.objects.filter(title__startswith=DEMO_SLIDE_PREFIX).delete()
        Address.objects.filter(user__in=demo_users).delete()
        demo_products.delete()
        Category.objects.filter(name__in=CATEGORY_NAMES).delete()

    def _demo_usernames(self) -> list[str]:
        return [
            os.getenv("DEMO_ADMIN_USERNAME", "demo_admin").strip(),
            os.getenv("DEMO_USER_USERNAME", "demo_user").strip(),
        ]

    def _seed_assets_dir(self, *parts: str) -> Path:
        return (
            Path(__file__).resolve().parent.parent.parent
            / "seed_assets"
            / Path(*parts)
        )

    def _sorted_numbered_assets(self, directory: Path, prefix: str) -> list[Path]:
        if not directory.is_dir():
            return []

        numbered_assets: list[tuple[int, Path]] = []
        for asset_path in directory.iterdir():
            if not asset_path.is_file():
                continue

            stem = asset_path.stem.lower()
            if not stem.startswith(prefix.lower()):
                continue

            suffix = stem[len(prefix):]
            if suffix.isdigit():
                numbered_assets.append((int(suffix), asset_path))

        return [
            asset_path
            for _number, asset_path in sorted(numbered_assets, key=lambda item: item[0])
        ]

    def _seed_categories(self) -> dict[str, Any]:
        Category = apps.get_model("products", "Category")
        category_fields = model_field_names(Category)
        categories: dict[str, Any] = {}

        for name in CATEGORY_NAMES:
            defaults: dict[str, Any] = {}
            if "slug" in category_fields:
                defaults["slug"] = slugify(name, allow_unicode=False)
            if "is_active" in category_fields:
                defaults["is_active"] = True

            category, _created = Category.objects.get_or_create(
                name=name,
                defaults=defaults,
            )
            categories[name] = category

        return categories

    def _seed_products(self, categories: dict[str, Any]) -> list[Any]:
        Product = apps.get_model("products", "Product")
        product_fields = model_field_names(Product)
        products: list[Any] = []

        for item in DEMO_PRODUCTS:
            defaults: dict[str, Any] = {
                "category": categories[item["category"]],
                "description": item["description"],
                "price": item["price"],
                "stock": item["stock"],
                "is_active": True,
                "has_colors": False,
                "has_sizes": False,
            }

            for field_name, value in list(defaults.items()):
                if field_name not in product_fields:
                    defaults.pop(field_name)

            if "slug" in product_fields:
                defaults["slug"] = slugify(item["name"], allow_unicode=False)

            product, _created = Product.objects.update_or_create(
                name=item["name"],
                defaults=defaults,
            )
            products.append(product)

        return products

    def _seed_product_images(self, products: list[Any]) -> int:
        ProductImage = apps.get_model("products", "ProductImage")
        products_dir = self._seed_assets_dir("products")
        product_assets = self._sorted_numbered_assets(products_dir, "product")

        if not product_assets:
            self.stdout.write(
                self.style.WARNING(
                    "No product images found in core/seed_assets/products; skipping."
                )
            )
            return 0

        demo_product_ids = [product.pk for product in products]
        ProductImage.objects.filter(product_id__in=demo_product_ids).delete()

        for index, product in enumerate(products):
            asset_path = product_assets[index % len(product_assets)]
            product_image = ProductImage(product=product, order=0)
            with asset_path.open("rb") as asset_file:
                product_image.image.save(
                    asset_path.name,
                    File(asset_file),
                    save=True,
                )

        return len(products)

    def _seed_demo_users(self) -> tuple[Any, Any]:
        User = get_user_model()

        admin_username = os.getenv("DEMO_ADMIN_USERNAME", "demo_admin").strip()
        admin_email = os.getenv(
            "DEMO_ADMIN_EMAIL",
            "admin@example.com",
        ).strip().lower()
        admin_password = os.getenv("DEMO_ADMIN_PASSWORD", "ChangeMeAdmin123!")

        user_username = os.getenv("DEMO_USER_USERNAME", "demo_user").strip()
        user_email = os.getenv(
            "DEMO_USER_EMAIL",
            "user@example.com",
        ).strip().lower()
        user_password = os.getenv("DEMO_USER_PASSWORD", "ChangeMeUser123!")

        admin_user, _admin_created = User.objects.update_or_create(
            username=admin_username,
            defaults={
                "email": admin_email,
                "first_name": "Demo",
                "last_name": "Administrator",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
                "phone_number": "5550000001",
                "birth_date": None,
                "tc_kimlik_no": None,
            },
        )
        admin_user.set_password(admin_password)
        admin_user.save()

        demo_user, _user_created = User.objects.update_or_create(
            username=user_username,
            defaults={
                "email": user_email,
                "first_name": "Demo",
                "last_name": "Customer",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
                "phone_number": "5550000002",
                "birth_date": None,
                "tc_kimlik_no": "12345678901",
            },
        )
        demo_user.set_password(user_password)
        demo_user.save()

        return admin_user, demo_user

    def _seed_addresses(self, demo_user: Any) -> list[Any]:
        Address = apps.get_model("users", "Address")
        Address.objects.filter(user=demo_user).delete()

        address_data = [
            ("Ev Adresim", "shipping", "Demo Customer", "5550000002", "Demoşehir", "Merkez", "Demo Mahallesi, Örnek Sokak No:1"),
            ("İş Adresim", "shipping", "Demo Customer", "5550000002", "Demoşehir", "Kuzey", "Örnek İş Merkezi, Demo Cad. No:10"),
            ("Fatura Adresim", "billing", "Demo Customer", "5550000002", "Demoşehir", "Güney", "Fatura Mah., Demo Bulvarı No:20"),
            ("Yazlık Ev", "shipping", "Demo Customer", "5550000002", "Örnek İl", "Sahil", "Sahil Mah., Demo Sokak No:5"),
            ("Aile Evi", "shipping", "Demo Customer 2", "5550000003", "Örnek İl", "Batı", "Batı Mah., Demo Cad. No:15"),
            ("Ofis Fatura", "billing", "Demo Customer", "5550000002", "Örnek İl", "Doğu", "OSB Demo Cad. No:7"),
        ]

        addresses: list[Any] = []
        for title, address_type, full_name, phone, city, district, address_line in address_data:
            address = Address.objects.create(
                user=demo_user,
                title=title,
                address_type=address_type,
                full_name=full_name,
                phone=phone,
                city=city,
                district=district,
                address_line=address_line,
                country="Türkiye",
            )
            addresses.append(address)

        return addresses

    def _seed_orders(
        self,
        demo_user: Any,
        products: list[Any],
        addresses: list[Any],
    ) -> tuple[list[Any], int]:
        Order = apps.get_model("orders", "Order")
        OrderItem = apps.get_model("orders", "OrderItem")

        Order.objects.filter(user=demo_user).delete()

        shipping_addresses = [
            address for address in addresses if address.address_type == "shipping"
        ]
        billing_address = next(
            address for address in addresses if address.address_type == "billing"
        )

        orders: list[Any] = []
        order_items_created = 0
        product_pool = products.copy()
        self._rng.shuffle(product_pool)
        product_index = 0

        for order_number, status in enumerate(ORDER_STATUS_PLAN):
            shipping_address = shipping_addresses[order_number % len(shipping_addresses)]
            created_at = timezone.now() - timedelta(days=45 - order_number * 2)

            order = Order.objects.create(
                user=demo_user,
                status=status,
                shipping_full_name=shipping_address.full_name,
                shipping_phone=shipping_address.phone,
                shipping_district=shipping_address.district,
                shipping_address=shipping_address.address_line,
                shipping_city=shipping_address.city,
                shipping_country=shipping_address.country,
                billing_full_name=billing_address.full_name,
                billing_phone=billing_address.phone,
                billing_address=billing_address.address_line,
                billing_city=billing_address.city,
                billing_district=billing_address.district,
                billing_country=billing_address.country,
                pre_information_approved=True,
                distance_contract_approved=True,
                contracts_approved_at=created_at,
                payment_method="iyzico" if status not in {"payment_failed", "cancelled"} else None,
                paid_at=created_at if status not in {"payment_failed", "cancelled", "draft"} else None,
                invoice_type="individual",
                invoice_identity_number="12345678901",
            )
            Order.objects.filter(pk=order.pk).update(
                created_at=created_at,
                updated_at=created_at,
            )
            order.refresh_from_db()

            item_count = ORDER_ITEM_COUNTS[order_number]
            for _ in range(item_count):
                product = product_pool[product_index % len(product_pool)]
                product_index += 1
                quantity = 1 + (product_index % 2)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                )
                order_items_created += 1

            order.calculate_totals()
            orders.append(order)

        return orders, order_items_created

    def _seed_favorites(self, demo_user: Any, products: list[Any]) -> int:
        Favorite = apps.get_model("users", "Favorite")
        Favorite.objects.filter(user=demo_user).delete()

        favorite_products = self._rng.sample(products, TARGET_FAVORITES)
        for product in favorite_products:
            Favorite.objects.create(user=demo_user, product=product)

        return TARGET_FAVORITES

    def _seed_ratings(
        self,
        demo_user: Any,
        admin_user: Any,
        products: list[Any],
    ) -> tuple[int, int]:
        ProductRating = apps.get_model("products", "ProductRating")
        ProductRating.objects.filter(user__in=[demo_user, admin_user]).delete()

        rated_products = self._rng.sample(products, TARGET_RATINGS)
        review_products = set(self._rng.sample(rated_products, TARGET_REVIEWS))

        for index, product in enumerate(rated_products):
            user = demo_user if index < 30 else admin_user
            review_text = None
            if product in review_products:
                review_text = REVIEW_TEXTS[index % len(REVIEW_TEXTS)]

            ProductRating.objects.create(
                user=user,
                product=product,
                rating=3 + (index % 3),
                review=review_text,
            )

        return TARGET_RATINGS, TARGET_REVIEWS

    def _seed_campaigns(self, products: list[Any]) -> int:
        BulkDiscount = apps.get_model("products", "BulkDiscount")
        demo_product_ids = [product.pk for product in products]
        BulkDiscount.objects.filter(product_id__in=demo_product_ids).delete()

        campaign_products = self._rng.sample(products, TARGET_CAMPAIGNS)
        thresholds = [2, 3, 5, 10]
        discounts = [10, 15, 20, 25]

        for index, product in enumerate(campaign_products):
            BulkDiscount.objects.create(
                product=product,
                quantity_threshold=thresholds[index],
                discount_percent=discounts[index],
            )

        return TARGET_CAMPAIGNS

    def _make_slide_image(self, color: tuple[int, int, int], filename: str) -> ContentFile:
        image = Image.new("RGB", (1920, 840), color)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        return ContentFile(buffer.getvalue(), name=filename)

    def _seed_slides(self) -> int:
        HomeSlide = apps.get_model("pages", "HomeSlide")
        HomeSlide.objects.filter(title__startswith=DEMO_SLIDE_PREFIX).delete()

        slides_dir = self._seed_assets_dir("slides")
        slide_assets = self._sorted_numbered_assets(slides_dir, "slide")

        if slide_assets:
            for index, asset_path in enumerate(slide_assets):
                title = (
                    SLIDE_TITLES[index]
                    if index < len(SLIDE_TITLES)
                    else f"Demo Slide {index + 1}"
                )
                slide = HomeSlide(
                    title=f"{DEMO_SLIDE_PREFIX} {title}",
                    order=index,
                )
                with asset_path.open("rb") as asset_file:
                    slide.image.save(
                        asset_path.name,
                        File(asset_file),
                        save=False,
                    )
                slide.save()
            return len(slide_assets)

        self.stdout.write(
            self.style.WARNING(
                "No slide images found in core/seed_assets/slides; using placeholders."
            )
        )
        for index, color in enumerate(SLIDE_FALLBACK_COLORS):
            title = SLIDE_TITLES[index]
            slide = HomeSlide(
                title=f"{DEMO_SLIDE_PREFIX} {title}",
                order=index,
            )
            slide.image.save(
                f"demo-slide-{index + 1}.jpg",
                self._make_slide_image(color, f"demo-slide-{index + 1}.jpg"),
                save=False,
            )
            slide.save()

        return len(SLIDE_FALLBACK_COLORS)

    def _seed_contact_messages(self) -> int:
        ContactMessage = apps.get_model("users", "ContactMessage")
        ContactMessage.objects.filter(subject__startswith=DEMO_CONTACT_PREFIX).delete()

        for name, email, phone, subject, message in CONTACT_MESSAGES:
            ContactMessage.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=f"{DEMO_CONTACT_PREFIX} {subject}",
                message=message,
                is_read=bool(self._rng.getrandbits(1)),
            )

        return TARGET_MESSAGES

    def _seed_return_requests(self, demo_user: Any, orders: list[Any]) -> int:
        ReturnRequest = apps.get_model("orders", "ReturnRequest")
        ReturnRequest.objects.filter(user=demo_user).delete()

        eligible_orders = [
            order for order in orders if order.status in {"delivered", "shipped"}
        ]
        reasons = ["defective", "wrong_item", "not_as_described"]

        for index in range(TARGET_RETURNS):
            order = eligible_orders[index]
            order_item = order.items.first()
            ReturnRequest.objects.create(
                order=order,
                order_item=order_item,
                user=demo_user,
                quantity=1,
                reason=reasons[index],
                reason_detail=(
                    f"{DEMO_MARKER} Demo mağaza iade talebi. "
                    "Ürün beklentiyi karşılamadı."
                ),
                status=["pending", "approved", "received"][index],
            )

        return TARGET_RETURNS

    def _seed_site_configuration(self) -> None:
        try:
            Site = apps.get_model("sites", "Site")
        except LookupError:
            return

        Site.objects.update_or_create(
            id=1,
            defaults={
                "domain": "localhost:8080",
                "name": f"{settings.STORE_NAME} Demo Store",
            },
        )

    def _seed_order_settings(self) -> None:
        OrderSetting = apps.get_model("orders", "OrderSetting")
        OrderSetting.objects.get_or_create(
            pk=1,
            defaults={
                "shipping_fee": Decimal("100.00"),
                "free_shipping_limit": Decimal("1000.00"),
            },
        )

    def _print_summary(self) -> None:
        divider = "=" * 41
        lines = [
            divider,
            "Demo Store Successfully Created",
            divider,
            "",
            f"Categories : {self.stats.categories}",
            f"Products   : {self.stats.products}",
            f"Users      : {self.stats.users}",
            f"Addresses  : {self.stats.addresses}",
            f"Orders     : {self.stats.orders}",
            f"Favorites  : {self.stats.favorites}",
            f"Ratings    : {self.stats.ratings}",
            f"Campaigns  : {self.stats.campaigns}",
            f"Slides     : {self.stats.slides}",
            f"Messages   : {self.stats.messages}",
            f"Returns    : {self.stats.returns}",
            "",
            "Admin:",
            self.stats.admin_username,
            "",
            "Customer:",
            self.stats.customer_username,
            "",
            "http://localhost:8080",
            divider,
        ]

        for line in lines:
            self.stdout.write(line)
