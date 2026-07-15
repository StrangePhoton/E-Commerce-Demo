from django.conf import settings


def get_store_context() -> dict[str, str]:
    """Return demo-safe store branding values for templates and services."""
    return {
        "STORE_NAME": settings.STORE_NAME,
        "STORE_LEGAL_NAME": settings.STORE_LEGAL_NAME,
        "STORE_TAGLINE": settings.STORE_TAGLINE,
        "STORE_EMAIL": settings.STORE_EMAIL,
        "STORE_SUPPORT_EMAIL": settings.STORE_SUPPORT_EMAIL,
        "STORE_PRIVACY_EMAIL": settings.STORE_PRIVACY_EMAIL,
        "STORE_LEGAL_EMAIL": settings.STORE_LEGAL_EMAIL,
        "STORE_PHONE": settings.STORE_PHONE,
        "STORE_PHONE_TEL": settings.STORE_PHONE_TEL,
        "STORE_WHATSAPP_URL": settings.STORE_WHATSAPP_URL,
        "STORE_ADDRESS": settings.STORE_ADDRESS,
        "STORE_CITY": settings.STORE_CITY,
        "STORE_DOMAIN": settings.STORE_DOMAIN,
        "STORE_URL": settings.STORE_URL,
        "STORE_MERSIS": settings.STORE_MERSIS,
        "STORE_TAX_NUMBER": settings.STORE_TAX_NUMBER,
        "STORE_SLOGAN": settings.STORE_SLOGAN,
        "STORE_INSTAGRAM_URL": settings.STORE_INSTAGRAM_URL,
        "STORE_LOGO": settings.STORE_LOGO,
        "ADMIN_NOTIFICATION_EMAIL": settings.ADMIN_NOTIFICATION_EMAIL,
    }
