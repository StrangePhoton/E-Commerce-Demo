# Django E-Commerce Platform (Demo)

Public demo repository for a full-featured Django e-commerce application.  
All company names, contact details, legal texts, and customer data are **placeholder/demo values** and safe to publish.

**Live demo target:** `http://localhost:8080`

> **Important:** This repository is a **sanitized demo version** for portfolio and evaluation purposes only. The commercial product was licensed to a client; **all software rights remain with the author**. Unauthorized commercial use, resale, or client deployment is prohibited. See [LICENSE](LICENSE).

---

## Features

- Product catalog with categories, images, ratings, and bulk discounts
- User accounts, addresses, favorites, and profile management
- Shopping cart and multi-step checkout
- Order lifecycle (draft → payment → shipping → delivery / returns)
- Admin dashboard (products, orders, campaigns, slides, contact messages)
- Iyzico sandbox payment integration
- Docker-based local stack (PostgreSQL, Redis, Nginx, Gunicorn)
- Repeatable demo store seed command

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.1 |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| App server | Gunicorn |
| Reverse proxy | Nginx |
| Payments | Iyzico (sandbox) |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose)

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd django-ecommerce-platform

cp .env.example .env
```

Edit `.env` if needed. Defaults are fine for local demo.

### 2. Start the stack

```bash
docker compose up --build -d
```

Wait until all services are healthy, then open:

**http://localhost:8080**

### 3. Seed the demo store

```bash
docker compose exec web python manage.py seed_demo_data --reset
```

Expected output:

```
=========================================
Demo Store Successfully Created
=========================================

Categories : 7
Products   : 65
Users      : 2
...
Admin:
demo_admin

Customer:
demo_user
```

### 4. Demo logins

| Role | Username | Password (default) |
|------|----------|--------------------|
| Admin | `demo_admin` | `ChangeMeAdmin123!` |
| Customer | `demo_user` | `ChangeMeUser123!` |

Admin panel: **http://localhost:8080/yonetim/**

---

## Demo Data

The `seed_demo_data` command creates a complete fictional store:

| Entity | Count |
|--------|-------|
| Categories | 7 |
| Products | 65 |
| Users | 2 |
| Addresses | 6 |
| Orders | 18 |
| Order lines | 40 |
| Favorites | 12 |
| Ratings | 35 |
| Reviews | 18 |
| Campaigns | 4 |
| Slides | 3 |
| Contact messages | 6 |
| Return requests | 3 |

Product and slide images are loaded from `core/seed_assets/`.

---

## Environment Variables

Copy `.env.example` to `.env`. Never commit `.env`.

### Core

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Debug mode (`True` for local demo) |
| `APP_BASE_URL` | Public app URL (`http://localhost:8080`) |

### Store branding (demo-safe defaults)

| Variable | Example |
|----------|---------|
| `STORE_NAME` | `Demo Health Store` |
| `STORE_LEGAL_NAME` | `Demo Medikal Ltd. Şti.` |
| `STORE_EMAIL` | `support@demo-store.example` |
| `STORE_PHONE` | `+90 555 000 00 00` |
| `STORE_ADDRESS` | Demo address |
| `STORE_DOMAIN` | `demo-store.example` |
| `STORE_LOGO` | `images/demo-logo.svg` |

### Payments (optional for sandbox)

| Variable | Description |
|----------|-------------|
| `IYZICO_API_KEY` | Iyzico sandbox API key |
| `IYZICO_SECRET_KEY` | Iyzico sandbox secret |
| `IYZICO_BASE_URL` | `https://sandbox-api.iyzipay.com` |

Leave payment keys empty to run the storefront without live payments.

---

## Useful Commands

```bash
# View logs
docker compose logs -f web

# Django shell
docker compose exec web python manage.py shell

# Rebuild after code changes
docker compose up --build -d web

# Reset demo data
docker compose exec web python manage.py seed_demo_data --reset

# Secret scan before publishing
python scripts/scan_secrets.py
```

---

## Project Structure

```
django-ecommerce-platform/
├── angelesyasam/          # Django project settings
├── cart/                  # Shopping cart
├── core/                  # Shared utilities, seed command, demo assets
│   ├── seed_assets/       # Demo product/slide images
│   └── management/commands/seed_demo_data.py
├── orders/                # Orders, contracts, returns
├── pages/                 # Storefront pages, admin views
├── payments/              # Iyzico integration
├── products/              # Catalog
├── users/                 # Custom user model, addresses
├── templates/             # HTML templates
├── static/                # CSS, JS, demo logo
├── nginx/                 # Nginx config
├── scripts/               # Secret scan, branding tools
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Security Notes (Public Repo)

- `.env` is listed in `.gitignore` — do not commit it
- All real business data has been replaced with demo placeholders
- Run `python scripts/scan_secrets.py` before pushing to GitHub
- Change all default passwords before any non-local deployment
- Use Iyzico **sandbox** keys only in demo environments

---

## Publishing to GitHub

```bash
# 1. Initialize repository (if not done yet)
git init

# 2. Verify .env is ignored
git status
# .env should NOT appear in untracked/staged files

# 3. Scan for secrets
python scripts/scan_secrets.py

# 4. First commit
git add .
git commit -m "Initial public demo release"

# 5. Create GitHub repo and push
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

---

## License

This repository is **not** open source under MIT, Apache, or GPL.

It is published under a **custom demo license** ([LICENSE](LICENSE)) that allows:

- Learning, local testing, and portfolio review
- Non-commercial personal experimentation

It **does not** allow:

- Commercial use
- Resale or sublicensing
- Using the codebase for paid client projects without written permission

All software rights remain with the copyright holder.

---

## Disclaimer

This is a demonstration project. Company information, legal texts, bank details, and customer records are fictional. Do not use default credentials or placeholder values in production.

Unauthorized commercial use of this codebase is prohibited. For commercial licensing, contact the repository owner.
