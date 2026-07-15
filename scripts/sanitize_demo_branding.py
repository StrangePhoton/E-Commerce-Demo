#!/usr/bin/env python3
"""One-time helper to replace hardcoded store branding with template variables."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = [
    ("| Angeles Yaşam", "| {{ STORE_NAME }}"),
    ("Angeles Yaşam - Sağlık ve Yaşam Ürünleri", "{{ STORE_NAME }} - Demo Sağlık Ürünleri"),
    ("Angeles Yaşam - Doğal Yaşam, Mutlu Seçimler", "{{ STORE_NAME }} - {{ STORE_SLOGAN }}"),
    ("Angeles Yaşam - Şifre Sıfırlama", "{{ STORE_NAME }} - Şifre Sıfırlama"),
    ("Angeles Yaşam Medikal Ltd. Şti.", "{{ STORE_LEGAL_NAME }}"),
    ("angelesyasam@gmail.com", "{{ STORE_EMAIL }}"),
    ("+90 554 640 26 14", "{{ STORE_PHONE }}"),
    (
        "Kırmızıtoprak Mahallesi, Yenice Sk. NO:14, 26000 Odunpazarı/Eskişehir",
        "{{ STORE_ADDRESS }}",
    ),
    ("www.angelesyasam.com", "{{ STORE_DOMAIN }}"),
    ("ANGELES MEDİKAL", "{{ STORE_TAGLINE }}"),
    ("{% block title %}Angeles Yaşam{% endblock %}", "{% block title %}{{ STORE_NAME }}{% endblock %}"),
    (
        '<meta property="og:site_name" content="Angeles Yaşam">',
        '<meta property="og:site_name" content="{{ STORE_NAME }}">',
    ),
    ('<meta name="author" content="Angeles Yaşam">', '<meta name="author" content="{{ STORE_NAME }}">'),
    (
        "medikal ürünler, sağlık ürünleri, elektronik cihazlar, hasta bakım malzemeleri, Angeles Yaşam",
        "medikal ürünler, sağlık ürünleri, elektronik cihazlar, hasta bakım malzemeleri, demo mağaza",
    ),
    ("Angeles Yaşam - Sağlık ve yaşam kalitenizi", "{{ STORE_NAME }} - Demo sağlık mağazası"),
    ("Angeles Yaşam'a Hoş Geldiniz", "{{ STORE_NAME }}'a Hoş Geldiniz"),
    ("Angeles Yaşam, sağlık", "{{ STORE_NAME }}, demo sağlık"),
    ("Eskişehir merkezli firmamız", "{{ STORE_CITY }} merkezli demo mağazamız"),
    ("<strong>Angeles Yaşam</strong>", "<strong>{{ STORE_NAME }}</strong>"),
    ("Angeles Yaşam", "{{ STORE_NAME }}"),
    ("{% static 'images/logo.png' %}", "{% static STORE_LOGO %}"),
]

SKIP_DIRS = {".git", "venv", ".venv", "__pycache__", "media", "staticfiles", "seed_assets"}


def should_process(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix in {".html", ".txt"}


def main() -> None:
    changed_files = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_process(path):
            continue

        original = path.read_text(encoding="utf-8")
        updated = original
        for old, new in REPLACEMENTS:
            updated = updated.replace(old, new)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
            print(f"updated: {path.relative_to(ROOT)}")

    print(f"done: {changed_files} file(s)")


if __name__ == "__main__":
    main()
