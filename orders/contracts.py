from django.conf import settings
from django.utils import timezone


def generate_pre_information_text(order):
    """
    Pre-information text according to 6502 Law.
    """
    items_html = ""
    for item in order.items.all():
        items_html += f"- {item.product.name} ({item.quantity} Adet) - Birim Fiyat: {item.price} TL\n"

    return f"""
ÖN BİLGİLENDİRME FORMU

1. SATICI BİLGİLERİ
Unvan: {settings.STORE_LEGAL_NAME}
E-posta: {settings.STORE_LEGAL_EMAIL}
Sipariş No: {order.id}
Sipariş Tarihi: {order.created_at.strftime("%d.%m.%Y")}

2. ALICI BİLGİLERİ
Ad Soyad: {order.shipping_full_name}
Telefon: {order.shipping_phone}
Adres: {order.shipping_address} / {order.shipping_district} / {order.shipping_city}

3. SÖZLEŞME KONUSU ÜRÜN VE BEDEL BİLGİLERİ
Satın alınan ürünlerin detayları aşağıdadır:
{items_html}
Toplam Sipariş Tutarı (KDV Dahil): {order.total_price} TL
Ödeme Yöntemi: {order.get_payment_method_display() if order.payment_method else "Kredi Kartı / Banka Kartı"}

4. TESLİMAT BİLGİLERİ
Ürünler, yasal 30 günlük süreyi aşmamak kaydıyla belirtilen adrese teslim edilecektir. Kargo ücreti ve teslimat detayları ödeme sayfasında onayınıza sunulmuştur.

5. CAYMA HAKKI VE İSTİSNALAR
Medikal ürünler; sağlık ve hijyen açısından iadesi uygun olmayan (ambalajı açılmış, kullanılmış) ürünler kapsamında olduğundan, ambalajı açılan tıbbi sarf malzemelerinde cayma hakkı kullanılamaz.
"""


def generate_distance_sales_contract(order):
    """
    Yasal olarak bağlayıcı Mesafeli Satış Sözleşmesi.
    """
    items_html = ""
    for item in order.items.all():
        items_html += f"- {item.product.name} ({item.quantity} Adet) x {item.price} TL\n"

    return f"""
MESAFELİ SATIŞ SÖZLEŞMESİ

İŞBU SÖZLEŞME ELEKTRONİK ORTAMDA ONAYLANDIĞI AN YÜRÜRLÜĞE GİRER.

1. TARAFLAR
SATICI: {settings.STORE_LEGAL_NAME} (Bundan sonra “SATICI” olarak anılacaktır)
ALICI: {order.shipping_full_name} (Bundan sonra “ALICI” olarak anılacaktır)
Adres: {order.shipping_address} / {order.shipping_district} / {order.shipping_city}

2. KONU
İşbu sözleşmenin konusu; SATICI’ya ait internet sitesi üzerinden sipariş verilen aşağıda detayları belirtilen medikal ürünlerin satışı ve teslimine ilişkin tarafların hak ve yükümlülüklerinin belirlenmesidir.

3. ÜRÜN VE SİPARİŞ BİLGİLERİ
Sipariş No: {order.id}
Sipariş İçeriği:
{items_html}
GENEL TOPLAM: {order.total_price} TL

4. MEDİKAL ÜRÜNLERE İLİŞKİN ÖNEMLİ BİLGİLENDİRME
{settings.STORE_NAME} tarafından satışa sunulan ürünlerin tamamı veya büyük çoğunluğu; tıbbi cihaz ve sağlık ürünü niteliğindedir. ALICI, medikal ürünlerin yanlış veya yetkisiz kullanımından doğabilecek sonuçlardan SATICI’nın sorumlu olmadığını kabul eder.

5. CAYMA HAKKI VE YASAL İSTİSNALAR
Mesafeli Sözleşmeler Yönetmeliği’nin 15. maddesi uyarınca; sağlık ve hijyen açısından iadesi uygun olmayan, ambalajı açılmış, kullanılmış veya tek kullanımlık medikal ürünlerde cayma hakkı bulunmamaktadır. ALICI, siparişi onaylayarak bu kısıtlamayı kabul etmiş sayılır.

6. TESLİMAT VE GENEL ESASLAR
Sipariş edilen ürünler, yasal azami süreler aşılmamak kaydıyla ALICI’ya teslim edilir.

7. YETKİLİ MAHKEME
İşbu sözleşmeden doğabilecek uyuşmazlıklarda, ALICI’nın yerleşim yerindeki Tüketici Hakem Heyetleri veya Tüketici Mahkemeleri yetkilidir.

Sözleşme Tarihi: {timezone.now().strftime("%d.%m.%Y %H:%M")}
"""
