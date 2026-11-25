# Antique Hub – System Architecture & Engineering Technical Guide

> **Enterprise Architecture & Technical Knowledgebase** | Comprehensive Engineering Documentation on Platform Rationale, Data Flow Diagrams (DFD), Entity-Relationship (ER) Design, Django Web Architecture, and Security Implementation

---

## Table of Contents
1. [Section 1: Project Overview, Objectives & Architecture](#section-1-project-overview-objectives--architecture)
2. [Section 2: Data Flow Diagrams (DFD) Decomposition (Levels 0, 1 & 2)](#section-2-data-flow-diagrams-dfd-decomposition-levels-0-1--2)
3. [Section 3: Entity-Relationship (ER) Design & Database Schema](#section-3-entity-relationship-er-design--database-schema)
4. [Section 4: Django & Web Engineering Core Concepts](#section-4-django--web-engineering-core-concepts)
5. [Section 5: Security Engineering, Testing & Performance](#section-5-security-engineering-testing--performance)

---

## Section 1: Project Overview, Objectives & Architecture

### Q1: What is the primary problem statement and objective of Antique Hub?
**Answer:**  
Generic e-commerce platforms (e.g., Amazon, Flipkart) are engineered for mass-manufactured goods with abundant, replaceable inventory. They are ill-suited for the antique and cultural antiquities domain, which requires:
1. **Provenance & Verification:** Every artifact has unique historical age, cultural origin, and metallurgical or metallurgical patina condition.
2. **Scarcity & Non-Replenishable Stock:** Antique artifacts cannot be factory backordered. When stock is exhausted, it is sold out permanently or until a new historical piece arrives.
3. **Marketplace Trust & Authentication:** A specialized escrow/vetting process where sellers must be verified by an Administrator before listing items.
4. **Regulatory Awareness:** Compliance with heritage trading guidelines, preventing illicit trafficking by recording provenance details.

**Antique Hub** addresses these challenges through a curated multi-vendor marketplace featuring verified seller onboarding, multi-angle provenance documentation, atomic inventory row-locking, PCI-DSS compliant sandbox payment processing, and comprehensive administrative oversight.

---

### Q2: What are the primary user roles in Antique Hub, and how are their boundaries enforced?
**Answer:**  
Antique Hub implements **Role-Based Access Control (RBAC)** across three distinct user roles:
- **Administrator (Superuser/Staff):** Oversees platform health, activates or deactivates pending sellers, blocks abusive users, creates and edits categories/subcategories, sets promotional discounts, moderates comments/FAQs, and inspects 6 live audit ledgers with CSV/PDF exports.
- **Seller (Vendor):** Uploads antique items with multi-image previews, manages arrived vs available stock, tracks customer orders for their items, and reviews customer feedback.
- **Buyer (Collector/Customer):** Browses and searches the marketplace catalog, manages a personal watchlist, adds items to cart up to available stock, confirms orders, pays via Luhn-validated credit/debit card or COD, downloads printable tax receipts, tracks delivery timelines, and posts verified reviews.

Access control is enforced at both the URL routing and view layers using custom Python decorators (`@admin_required`, `@seller_required`, and `@login_required`).

---

### Q3: Explain the high-level technology stack used in this project.
**Answer:**  
- **Backend Framework:** **Python 3.13 & Django 5.x/6.x** — selected for rapid development, robust built-in ORM, automated security features (CSRF, SQLi, XSS defenses), and clean MVT separation.
- **Database Layer:** **MySQL 8.0** for production (supporting strict relational foreign keys, transactions, and indexing) with automatic fallback to **SQLite 3** for local offline testing.
- **Frontend / Styling:** **HTML5, Vanilla CSS3, and Bootstrap 5.3** — customized with a rich antique aesthetic (dark parchment `#0d0d0d`, antique gold `#D4AF37`, and Cinzel typography).
- **Data Visualization:** **Chart.js** for interactive monthly revenue trends and category distribution charts on the Admin Dashboard.
- **Document Generation:** **ReportLab 4.x** for dynamic, server-side generation of administrative PDF audit reports.
- **Image Processing:** **Pillow 10.x** for validating, processing, and thumbnailing uploaded artifact images.

---

### Q4: How does the application switch between MySQL and SQLite without code modifications?
**Answer:**  
Database configuration is externalized into the `.env` file via `python-dotenv`. In `antique_hub/settings.py`, the system inspects the `DB_ENGINE` environment variable:
```python
DB_ENGINE = os.getenv('DB_ENGINE', 'mysql').lower()
if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'antique_hub_db'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
```
This enables seamless development on local machines without requiring a running MySQL server, while retaining full enterprise MySQL capabilities in production.

---

## Section 2: Data Flow Diagrams (DFD) Decomposition (Levels 0, 1 & 2)

```
                            ┌────────────────────────────────────────┐
                            │               LEVEL 0                  │
                            │           CONTEXT DIAGRAM              │
                            └───────────────────┬────────────────────┘
                                                │
                                                ▼
                            ┌────────────────────────────────────────┐
                            │               LEVEL 1                  │
                            │        FUNCTIONAL DECOMPOSITION        │
                            │  (1.0 Buyer, 2.0 Seller, 3.0 Admin)    │
                            └───────────────────┬────────────────────┘
                                                │
                                                ▼
                            ┌────────────────────────────────────────┐
                            │               LEVEL 2                  │
                            │        DETAILED PROCESS FLOWS          │
                            │  (1.1 Search, 1.2 Cart, 1.3 Order,     │
                            │   1.4 Payment, 2.1 Stock, 3.1 Reports) │
                            └────────────────────────────────────────┘
```

### Q5: What is a Context-Level Diagram (DFD Level 0), and how does it apply to Antique Hub?
**Answer:**  
A **DFD Level 0 (Context Diagram)** represents the entire system as a single central process, showing the primary external entities (actors) and the high-level data flows into and out of the system.

- **Central Process:** `0.0 Antique Hub Marketplace System`
- **External Entities:**
  1. **Buyer:** Sends registration data, search queries, cart additions, and payment details; receives search results, invoices, and order status updates.
  2. **Seller:** Sends artifact listings, provenance data, and stock replenishment updates; receives order notifications and customer feedback.
  3. **Administrator:** Sends approval/rejection flags, category updates, and discount rules; receives platform metrics, audit reports, and user activity logs.
  4. **Payment Gateway:** Receives card authorization requests; returns transaction reference tokens and payment status (Success/Failed).

---

### Q6: Walk through the Level 1 DFD Functional Decomposition.
**Answer:**  
DFD Level 1 decomposes the single Level 0 process into core business sub-processes:
- **Process 1.0 (Buyer Management & Shopping Flow):** Sub-processes include registration, authentication, browsing/searching artifacts, managing watchlist, updating cart, placing orders, and submitting payments.
- **Process 2.0 (Seller Catalog & Inventory Flow):** Sub-processes include seller registration (pending state), catalog listing upload, stock arrival logging, order fulfillment review, and comment tracking.
- **Process 3.0 (Administrative Governance & Analytics):** Sub-processes include seller verification/activation, user blocking, category CRUD, promotional discount management, FAQ moderation, and audit report generation.
- **Data Stores Connected:**
  - `D1: user_profile`
  - `D2: catalog_item`
  - `D3: inventory_stock`
  - `D4: cart`
  - `D5: purchase_master & purchase`
  - `D6: payment`
  - `D7: comment & review`
  - `D8: watchlisted`

---

### Q7: Explain DFD Processes 1.2, 1.2.1, 1.3, and 1.3.1 (Cart & Order Checkout Flow).
**Answer:**  
- **Process 1.2 (Add / Update Cart):** Buyer specifies item and quantity. The system queries `D3: inventory_stock` to ensure $quantity \le cur\_stock$. If stock is sufficient, `D4: cart` is updated.
- **Process 1.2.1 (Remove Item from Cart):** Confirms deletion via modal and deletes the item row from `D4: cart`.
- **Process 1.3 (Order Checkout & Stock Decrement):** When the buyer confirms the order, an atomic database transaction:
  1. Creates a `PurchaseMaster` record in `D5` (`status='Pending'`, `pay_status='Unpaid'`).
  2. Creates line items in `Purchase` table with price snapshots.
  3. Executes atomic row-locking on `D3: inventory_stock` (`select_for_update()`) and decrements `cur_stock` by the ordered quantity.
  4. Deletes active cart entries for the buyer from `D4`.
- **Process 1.3.1 (Payment Authorization):** Buyer enters card credentials. Gateway verifies Luhn Mod-10 checksum; upon success, writes transaction token to `D6: payment`, updates `PurchaseMaster` to `pay_status='Paid'`, `status='Confirmed'`, and returns a printable invoice.

---

### Q8: What occurs in DFD 3.0, 3.1, and 3.2 regarding Inventory Control and Cancellation?
**Answer:**  
- **DFD 3.0 (Initial Stock Creation):** When a seller publishes an item, opening stock $Q$ is recorded such that $tot\_arr\_stock = Q$ and $cur\_stock = Q$.
- **DFD 3.1 (Stock Replenishment):** When seller receives new inventory of quantity $N$, system executes:
  $$tot\_arr\_stock \leftarrow tot\_arr\_stock + N$$
  $$cur\_stock \leftarrow cur\_stock + N$$
- **DFD 3.2 (Order Cancellation & Restock):** If a buyer cancels an unshipped order of quantity $M$, the system sets order status to `Cancelled` and restores available stock:
  $$cur\_stock \leftarrow cur\_stock + M$$
  *Notice that $tot\_arr\_stock$ does not change, preserving total historical inventory throughput records.*

---

## Section 3: Entity-Relationship (ER) Design & Database Schema

```
  ┌──────────────┐          1:N          ┌───────────────────┐
  │  auth_user   │───────────────────────┤   userprofile     │
  └──────┬───────┘                       └───────────────────┘
         │
         │ 1:N (as Seller)
         ▼
  ┌──────────────┐          1:1          ┌───────────────────┐
  │     item     │───────────────────────┤       stock       │
  └──────┬───────┘                       └───────────────────┘
         │
         │ 1:N
         ▼
  ┌──────────────┐          N:1          ┌───────────────────┐
  │   purchase   │───────────────────────┤  purchase_master  │
  └──────────────┘                       └─────────┬─────────┘
                                                   │
                                                   │ 1:1
                                                   ▼
                                         ┌───────────────────┐
                                         │      payment      │
                                         └───────────────────┘
```

### Q9: Describe the core entities and their relationships in the ER model.
**Answer:**  
1. **User (`auth_user`) & UserProfile (`userprofile`):** 1-to-1 extension storing telephone, address, geographic keys (state, district, location), and account status (`Active`, `Pending`, `Inactive`).
2. **Role (`role`):** 1-to-Many with `userprofile` (Admin, Seller, Buyer).
3. **Geography (`state`, `district`, `location`):** Hierarchical 1-to-Many normalization ($State \rightarrow District \rightarrow Location$).
4. **Catalog (`category`, `subcategory`, `item`):** Hierarchical taxonomy where Category has many SubCategories, and SubCategory has many Items.
5. **Inventory (`item` & `stock`):** 1-to-1 relationship linking each artifact listing to its physical stock counter (`tot_arr_stock`, `cur_stock`).
6. **Orders (`purchase_master` & `purchase`):** 1-to-Many master-detail relationship representing order metadata and individual line items.
7. **Payment (`purchase_master` & `payment`):** 1-to-1 relationship storing sanitized transaction records and gateway tokens.
8. **Watchlist (`watchlisted`):** Many-to-Many junction between `auth_user` and `item` with a composite unique constraint `(user, item)` to prevent duplicates.
9. **Review (`comment`):** 1-to-Many relationship from `item` and `buyer` storing 1–5 star ratings and reviews.

---

### Q10: How is database normalization implemented up to 3NF in Antique Hub?
**Answer:**  
- **First Normal Form (1NF):** Every column contains atomic (indivisible) values. No repeating groups or comma-separated lists (e.g., multi-angle photographs use dedicated relational columns `img1`, `img2`, `img3` rather than a delimiter-separated text string).
- **Second Normal Form (2NF):** Satisfies 1NF, and all non-key attributes are fully functionally dependent on the primary key. In the composite junction table `watchlisted (user_id, item_id)`, `added_date` depends on the full composite key, avoiding partial dependencies.
- **Third Normal Form (3NF):** Satisfies 2NF and contains no transitive dependencies ($A \rightarrow B$ and $B \rightarrow C$). For example:
  - Geographical data is not embedded inside `userprofile`. Instead, it is normalized into `state`, `district`, and `location` tables. Storing city name directly in `userprofile` would create a transitive dependency on the state.
  - Category name is stored in `category`, referenced by `subcategory`, which is then referenced by `item`.

---

### Q11: How does Antique Hub achieve PCI-DSS compliance in its database design?
**Answer:**  
Under **PCI-DSS (Payment Card Industry Data Security Standard) Requirement 3**, merchants must protect stored cardholder data:
1. **Full PAN (Primary Account Number) Prohibition:** The system **never** stores the full 16-digit card number. Only the masked last 4 digits (e.g., `card_last4 = '4111'`) are persisted to allow customer card recognition on invoices.
2. **CVV / CVC Prohibition:** Card verification codes (CVV/CVV2) are strictly processed in memory during the gateway handshake and are **never** written to database storage or log files.
3. **Pseudonymization:** Transactions are tracked via a cryptographically random transaction reference token (`transaction_ref = 'TXN-AH-20261020-E050005D'`).

---

### Q12: Why is the purchase price snapshotted in the `Purchase` model?
**Answer:**  
Artifact prices fluctuate over time due to inflation, seller updates, or active promotional category discounts.  
If the order line item queried `item.price` dynamically in reports or receipts, any future price increase or discount expiration would retroactively alter past customer order totals, violating accounting integrity and legal tax compliance.

By snapshotting `price = item.discounted_price` in the `Purchase` table at the exact moment of order placement:
- The historical tax invoice and receipt remain immutable forever.
- Future price adjustments or discount changes only affect subsequent orders.

---

## Section 4: Django & Web Engineering Core Concepts

### Q13: Explain Django's MVT (Model-View-Template) architecture vs standard MVC.
**Answer:**  
Django follows the **MVT** architectural pattern:
- **Model:** Defines the data structure and business logic. Maps Python classes directly to database tables via the Django ORM (e.g., `catalog.models.Item`).
- **View:** Contains the controller logic and request handling. Receives HTTP requests, executes business rules, queries the Models, and passes context data to the Template (e.g., `orders.views.confirm_order`).
- **Template:** The presentation layer. Renders HTML with dynamic tags, filters, and variables using the Django Template Engine (e.g., `templates/payments/receipt.html`).

*In traditional MVC, the Controller handles routing and request management. In Django, the framework itself acts as the Controller (via URL routing and middleware), while the Django View serves as the controller logic.*

---

### Q14: How does Django's ORM prevent SQL Injection attacks?
**Answer:**  
Django's Object-Relational Mapper (ORM) avoids raw string concatenation in SQL queries. Instead, it uses **parameterized SQL queries** (prepared statements) by default:
```python
# User inputs malicious string: "' OR '1'='1"
query = request.GET.get('q')
items = Item.objects.filter(title__icontains=query)
```
Behind the scenes, Django passes the input as a bound query parameter rather than executing it as raw SQL syntax:
```sql
SELECT * FROM item WHERE title LIKE %s; -- Bound parameter: ['%\' OR \'1\'=\'1%']
```
The database engine treats the malicious payload strictly as literal text, preventing attackers from escaping string quotes, bypassing authentication, or executing arbitrary SQL commands.

---

### Q15: What is Cross-Site Request Forgery (CSRF), and how does Django protect against it?
**Answer:**  
**CSRF** is an attack where an unauthorized site tricks an authenticated user's browser into sending state-changing HTTP POST requests (e.g., placing an unauthorized order or transferring funds) by exploiting existing session cookies.

**Django's Defense Mechanism:**
1. **CSRF Middleware (`CsrfViewMiddleware`):** Generates a cryptographically random, secret token stored in a user cookie.
2. **Template Token (`{% csrf_token %}`):** Injects a hidden input field into every state-changing HTML `<form>`.
3. **Validation:** On receiving a POST request, Django checks that the token submitted in the form body matches the cookie token. If the token is missing or invalid, Django aborts the request with **HTTP 403 Forbidden**.

---

### Q16: How is Role-Based Access Control implemented using custom Python decorators?
**Answer:**  
Rather than duplicating authorization checks in every view, custom decorators wrap view functions to enforce access control cleanly:
```python
def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Access restricted to platform administrators.")
            return redirect('accounts:role_redirect')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
```
When applied (`@admin_required`), unauthenticated visitors are redirected to the login view, while authenticated non-admin users (such as Buyers) are intercepted and redirected to their role home page with an alert message.

---

### Q17: What is the difference between `select_related` and `prefetch_related` in Django ORM optimization?
**Answer:**  
Both methods solve the **N+1 query problem** when fetching related objects, but they use different SQL strategies:
- **`select_related` (Single-valued relationships: Foreign Key, One-to-One):**
  - Executes a single SQL query using an **SQL `INNER JOIN`** or `LEFT OUTER JOIN`.
  - Used in Antique Hub when fetching an Item and its Category or Seller Profile:
    ```python
    Item.objects.select_related('category', 'seller__userprofile')
    ```
- **`prefetch_related` (Multi-valued relationships: Many-to-Many, Reverse Foreign Keys):**
  - Executes separate SQL queries (one for the parent table, one for the child table) and joins them in Python memory using lookup dictionaries.
  - Used when fetching an Item and its multiple stock arrival records or active category discounts:
    ```python
    Item.objects.prefetch_related('stock_records', 'category__discounts')
    ```

---

### Q18: How does Antique Hub generate server-side PDF audit reports using ReportLab?
**Answer:**  
In `dashboard/views.py`, the `export_pdf` utility streams PDF data directly to the client browser without saving temporary files to disk:
1. Creates an in-memory byte buffer via `io.BytesIO()`.
2. Constructs a ReportLab `SimpleDocTemplate` with letter dimensions and landscape/portrait orientations.
3. Formats table headers and query rows with styled `Table` and `Paragraph` flowables.
4. Compiles the PDF into the buffer using `doc.build(elements)`.
5. Returns a `FileResponse` or `HttpResponse` with MIME type `application/pdf` and `Content-Disposition: attachment; filename="report.pdf"`.

---

## Section 5: Security Engineering, Testing & Performance

### Q19: What is Horizontal Privilege Escalation (IDOR), and how does Antique Hub prevent it?
**Answer:**  
**Insecure Direct Object Reference (IDOR)** occurs when an application exposes a database identifier (e.g., `/catalog/items/15/edit/`) and allows a user to access or manipulate another user's private records simply by modifying the ID parameter.

**Antique Hub's Defense:**  
In views where sellers modify or delete listings, the system validates item ownership before processing:
```python
item = get_object_or_404(Item, itemid=item_id)
is_admin = request.user.is_superuser or request.user.is_staff

if not is_admin and item.seller != request.user:
    raise PermissionDenied("You do not have permission to edit this antique listing.")
```
If Seller B attempts to POST edits to Seller A's item ID, Django raises a `PermissionDenied` exception and returns **HTTP 403 Forbidden**, keeping the original database listing unaltered.

---

### Q20: How does the Modulo-10 Luhn Algorithm validate payment card numbers?
**Answer:**  
The **Luhn Algorithm** (ISO/IEC 7812-1) is a checksum formula used to validate primary account numbers against accidental keystroke errors:
1. Start from the rightmost digit (the check digit) and move leftwards.
2. Double every second digit.
3. If doubling a digit results in a number greater than 9, sum its digits (e.g., $8 \times 2 = 16 \rightarrow 1 + 6 = 7$) or subtract 9.
4. Sum all processed digits.
5. If the total modulo 10 equals 0 ($total \pmod{10} = 0$), the card number is valid; otherwise, it is rejected.

In `payments/services.py`, this check runs prior to authorization to provide instant client/server feedback without sending invalid cards to the payment gateway.

---

### Q21: What password hashing algorithm does the application use, and why is it superior to MD5 or SHA1?
**Answer:**  
Antique Hub uses Django's default **PBKDF2 with SHA-256** hash algorithm with a work factor of **1,500,000 iterations**:
- **Format:** `pbkdf2_sha256$iterations$salt$hash`
- **Salt:** A cryptographically random unique string appended to each password prior to hashing, neutralizing precomputed rainbow-table lookup attacks.
- **Iterations (Key Stretching):** Requires 1.5 million SHA-256 computation cycles per password check, making brute-force dictionary attacks using modern GPUs prohibitively slow and expensive compared to legacy algorithms like MD5 or SHA-1 (which can be computed billions of times per second).

---

### Q22: What were the findings of the 500-item Performance Load Benchmark?
**Answer:**  
Using `scripts/performance_test.py`, the system generated 500 unique antique items and 500 stock records, then benchmarked 10 realistic search and filtering scenarios:
- **Default Marketplace Page 1 (500 items total):** 23.11 ms
- **Keyword Text Search ('Bronze'):** 20.74 ms
- **Category Filter Search:** 19.21 ms
- **Price Range Filter (₹10,000 to ₹50,000):** 19.16 ms
- **Sorting Ascending / Descending:** 20.53 ms – 21.08 ms
- **Combined Multi-Param Search (Keyword + Category + Sort):** 25.11 ms
- **Deep Pagination (Page 5):** 27.63 ms

**Conclusion:** Across all 10 operations, the overall average response time was **21.99 ms**, well below the target web application SLA of **< 200 ms**, demonstrating the efficiency of Django's indexing, `select_related` joins, and pagination.

---

### Q23: Summarize the results of the automated testing suite.
**Answer:**  
The test suite consists of **202 automated test cases** executed via Django's test runner, covering:
- Unit tests for all models, forms, and views across 8 core apps.
- Integration tests for multi-role workflows (Seller upload $\rightarrow$ Buyer search $\rightarrow$ Cart $\rightarrow$ Atomic order $\rightarrow$ Stock reduction $\rightarrow$ Luhn payment $\rightarrow$ Tax invoice).
- Dedicated security tests covering RBAC isolation, cross-seller IDOR prevention, CSRF enforcement, SQL injection resilience, XSS sanitization, and PBKDF2 cryptographic storage.

**Test Execution Result:**  
`Ran 202 tests in 161.179s — OK (0 Failures, 0 Errors, 100% Pass Rate).`
