# Antique Hub – Online Antique & Heritage Marketplace

> **Enterprise Platform Documentation** | Premier Curated Multi-Vendor Marketplace for Rare Antiquities  
> **Tech Stack:** Python 3.13 | Django 5.x / 6.x | MySQL 8.0 & SQLite | Bootstrap 5.3 | Pillow | ReportLab | Chart.js

---

## 1. Project Overview

**Antique Hub** is an authentic, multi-vendor online marketplace engineered specifically for cataloging, trading, and preserving historical antiques, sacred bronzes, royal weaponry, imperial numismatics, and vintage furniture.

Unlike conventional e-commerce platforms, Antique Hub addresses the unique challenges of the antique domain:
- **Strict Provenance & Authenticity:** Detailed age, cultural origin, multi-angle imagery, and microscopic patina examination records.
- **Stock Integrity & Scarcity:** Antique items are rare and strictly limited in quantity; atomic database row-locking (`select_for_update()`) ensures stock is only decremented upon successful order confirmation, preventing overselling.
- **Pluggable PCI-DSS Demo Payment Gateway:** Validates credit/debit cards using the **Modulo-10 Luhn Algorithm**, checks future expiration dates, detects card networks (Visa, MasterCard, RuPay, Amex), and stores strictly masked data (only the last 4 digits, bank name, card type, and transaction reference ID). Raw card numbers and CVV codes are never stored.
- **Role-Based Access Control (RBAC):** Three isolated user roles (**Administrator**, **Seller**, and **Buyer**) protected by custom security decorators and horizontal privilege escalation prevention (IDOR defenses).
- **Audit Reports & Analytics:** Live analytics with interactive Chart.js visualizations, real-time metrics, and instant **CSV / PDF report generation** via ReportLab for Users, Items, Orders, Sales, Payments, and Stock.

---

## 2. Architecture & Modules Synopsis

| Module | Title | Key Architectural Highlights |
|---|---|---|
| **Module 1** | Accounts & RBAC | Unified common login, role redirection, Indian 10-digit phone regex validation, duplicate username/email checking, and encrypted password hashing via PBKDF2-SHA256. |
| **Module 2** | Geography & Locations | Cascading AJAX dropdowns (State $\rightarrow$ District $\rightarrow$ Location) for localized seller shop fronts and delivery zones. |
| **Module 3** | Categories & SubCategories | Administrative hierarchical taxonomy management preventing accidental cascading deletion when items are attached. |
| **Module 4** | Item Management | Multi-angle image uploads with preview, provenance history, condition reports, and seller item management. |
| **Module 5** | Inventory & Stock | Total arrived stock tracking vs current available stock with automated out-of-stock badge synchronization. |
| **Module 6** | Marketplace Catalogue | Faceted multi-parameter search (keyword text, category, price range, historical era age), multi-column sorting, and pagination. |
| **Module 7** | Cart & Orders | Quantity capping to available stock, wash-trading prevention (sellers cannot purchase own items), atomic checkout, and order timeline tracking. |
| **Module 8** | Payments & Tax Invoices | Modulo-10 Luhn algorithm card verification, pluggable sandbox gateway, PCI-DSS compliance, and printable tax invoice generation. |
| **Module 9** | Comments & Reviews | Verified buyer reviews, 1-to-5 star ratings, input sanitization, and automated profanity masking (`i****`, `s***`). |
| **Module 10** | Watchlist | AJAX heart toggle, duplicate prevention, and administrative most-watched artifacts intelligence report (DFD 3.0). |
| **Module 11** | FAQ Knowledge Base | Administrative FAQ CRUD, and buyer/seller searchable Bootstrap 5 accordion covering authenticity, shipping, and returns. |
| **Module 12** | Discounts & Pricing | Category-wide percentage discounts with date-range validation, uniform effective price computation, and price snapshots on orders. |
| **Module 13** | Admin Dashboard | KPI metric cards, pending seller activation quick-actions, Chart.js monthly revenue trends, and 6 audit reports with CSV/PDF exports. |
| **Module 14** | UI & Accessibility | Rich antique aesthetic (dark parchment tones, gold `#D4AF37` highlights, Cinzel typography), responsive layout, and custom 404/403/500 handlers. |
| **Module 15** | Testing Engineering | 202 automated unit/integration/security tests, end-to-end purchase flow script, and 500-item load benchmark (< 22ms latency). |
| **Module 16** | Final Documentation | Comprehensive setup guide, MySQL seed dump, User Manual, Deployment notes, and System Architecture guide. |

---

## 3. System Requirements & Prerequisites

- **Operating System:** Windows 10/11, macOS, or Linux (Ubuntu 20.04/22.04 LTS recommended)
- **Python:** Python 3.10 to 3.13
- **Database:** MySQL 8.0+ or MariaDB 10.5+ (SQLite 3 is also supported out-of-the-box for local testing)
- **C/C++ Build Tools:** Required on Windows/Linux only if compiling `mysqlclient` from source (or use pre-built wheels)
- **Web Browser:** Google Chrome, Mozilla Firefox, Microsoft Edge, or Safari

---

## 4. Step-by-Step Installation & Setup

### Step 1: Clone or Extract the Repository
```bash
git clone https://github.com/your-username/antique_hub.git
cd antique_hub
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows (Command Prompt / PowerShell)
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the `.env.example` template to `.env`:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and configure your database settings:
```ini
# Django Secret Key and Debug Settings
SECRET_KEY=django-insecure-antique-hub-enterprise-secure-marketplace-key-2026
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database Engine: choose 'sqlite' or 'mysql'
DB_ENGINE=sqlite

# If DB_ENGINE=mysql, provide your MySQL credentials below:
DB_NAME=antique_hub_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

> **Note on MySQL:** If you choose `DB_ENGINE=mysql`, create the database first in MySQL:
> ```sql
> CREATE DATABASE antique_hub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> ```

### Step 5: Run Database Migrations
Initialize database tables:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Seed Master Demo Data
You can populate the database using either of the following two options:

#### Option A: Unified Python Seeder (Recommended for both SQLite & MySQL)
```bash
python scripts/seed_demo_data.py
```
*This command seeds roles, geographic regions, verified seller and buyer accounts, 10 authentic antique listings with stock, active category discounts, 8 curated FAQs, verified reviews, and demo orders.*

#### Option B: Direct MySQL SQL Dump Import (For MySQL users)
```bash
mysql -u root -p antique_hub_db < fixtures/seed_data.sql
```

### Step 7: Create Superuser (Optional)
If you did not run the seeder or want a custom admin:
```bash
python manage.py createsuperuser
```

### Step 8: Start the Local Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to:  
👉 **`http://127.0.0.1:8000/`**

---

## 5. Default Demonstration Accounts

The database seeder provisions pre-configured accounts for testing each role:

| Role | Username | Password | Status | Intended Demonstration |
|---|---|---|---|---|
| **Administrator** | `admin` | `AdminPass123!` | Active | Master Dashboard, Chart.js Analytics, User Activation, Reports Hub, FAQ CRUD |
| **Seller 1** | `chola_antiques` | `SellerPass123!` | Active | Sacred Bronzes specialist (Item uploads, Stock additions, Order fulfillment) |
| **Seller 2** | `deccan_relics` | `SellerPass123!` | Active | Numismatics & Coins specialist (Ledger viewing, Stock management) |
| **Seller 3** | `rajputana_heritage` | `SellerPass123!` | Active | Royal Armour & Weaponry specialist |
| **Seller 4** | `malabar_treasures` | `SellerPass123!` | **Pending** | Use this account to test the **Admin Seller Approval / Activation** workflow |
| **Buyer 1** | `collector_roy` | `BuyerPass123!` | Active | Verified Buyer (Search, Cart, Luhn Card Checkout, Tax Invoice, Reviews) |
| **Buyer 2** | `priya_curator` | `BuyerPass123!` | Active | Verified Buyer (Watchlist management, Multi-item purchases) |

---

## 6. Running the Automated Test Suite

Antique Hub includes an automated test engineering suite with **202 / 202 passing tests**:

```bash
# 1. Run the entire automated test suite (Unit, Integration & Security)
python manage.py test

# 2. Run only Integration workflow tests
python manage.py test orders.tests_integration

# 3. Run only Security & Access Control tests
python manage.py test accounts.tests_security

# 4. Execute the standalone Purchase Flow system script
python scripts/system_test_purchase_flow.py

# 5. Execute the 500-item Performance & Search Benchmark
python scripts/performance_test.py
```

---

## 7. Project Directory Layout

```
antique_hub/
├── manage.py                          # Django CLI entrypoint
├── requirements.txt                   # Production dependencies
├── .env.example                       # Environment template
├── db.sqlite3                         # Local SQLite database (if used)
├── antique_hub/                       # Core Project Configuration
│   ├── settings.py                    # Master Django settings (Security, DB, Static)
│   ├── urls.py                        # Top-level URL routing
│   ├── wsgi.py                        # WSGI entrypoint for Gunicorn/Waitress
│   └── views.py                       # HTTP 404, 403, 500 custom error handlers
├── accounts/                          # Module 1: Authentication & Profiles
├── locations/                         # Module 2: State, District, Location AJAX
├── catalog/                           # Modules 3, 4, 6: Category, SubCategory, Item
├── inventory/                         # Modules 5, 12: Stock Ledger, Discounts
├── orders/                            # Module 7: Cart, Checkout, Order Tracking
├── payments/                          # Module 8: Luhn Gateway, PCI Storage, Invoices
├── community/                         # Modules 9, 10, 11: Comments, Watchlist, FAQs
├── dashboard/                         # Module 13: Admin Dashboard, Charts, Reports
├── templates/                         # Module 14: Responsive UI Templates
│   ├── base.html                      # Antique-themed base master template
│   ├── 403.html, 404.html, 500.html   # Custom error fallback pages
│   └── ...                            # Role-based feature templates
├── static/                            # CSS, JavaScript, and Static Assets
├── media/                             # User-uploaded Antique Artifact Photographs
├── fixtures/
│   └── seed_data.sql                  # Enterprise MySQL 8 database seed dump
└── scripts/
    ├── seed_demo_data.py              # Master demo data seeder script
    ├── export_mysql_dump.py           # Dump generator utility
    ├── system_test_purchase_flow.py   # Full purchase flow system script
    └── performance_test.py            # High-scale 500-item latency benchmark
```

---

## 8. Platform Release Metadata

- **Platform Title:** Antique Hub – Online Antique & Heritage Marketplace
- **Release Version:** 1.0.0 Enterprise Edition
- **Architecture Standard:** Clean Relational Django Modular MVC
- **License:** Proprietary Commercial License
