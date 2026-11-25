# Antique Hub – User Manual & System Operational Guide

> **Enterprise Operations Manual** | Comprehensive Walkthrough for Platform Administrators, Verified Dealers, and Discerning Collectors

---

## 1. System Navigation & Role-Based Workflows

Antique Hub features three distinct user roles, each with strict permission boundaries and tailored user interfaces:

```
                                  [ Unauthenticated Visitor ]
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
         [ Browse Catalog & FAQs ]                        [ Register / Sign In ]
                                                                      │
                      ┌───────────────────────────────────────────────┴───────────────────────────────────────────────┐
                      ▼                                               ▼                                               ▼
               [ Buyer Role ]                                  [ Seller Role ]                                 [ Admin Role ]
         • Browse & Search Marketplace                   • Item Upload with Multi-Image                  • Master Analytics Dashboard
         • Watchlist Management                          • Stock Arrival & Ledger Control                • Pending Seller Activation
         • Cart Management                               • Order Fulfillment Console                     • User Block / Unblock Management
         • Order Placement & Tracking                    • Customer Feedback Ledger                      • Category & SubCategory CRUD
         • Luhn Card Payment Gateway                                                                     • Promotional Discounts Manager
         • Tax Invoice & Printable Receipt                                                               • FAQ Knowledge Base Editor
         • Verified Buyer Reviews                                                                        • 6 CSV & PDF Audit Reports Hub
```

---

## 2. Public Visitor Guide

### 2.1 Heritage Landing Page (`/`)
- **Visual Aesthetic:** Rich dark parchment canvas (`#0d0d0d`), antique gold accents (`#D4AF37`), and classic serif typography.
- **Hero Section:** Features call-to-action buttons: *"Explore Marketplace"* and *"Register as Collector / Seller"*.
- **Featured Artifacts Carousel:** Displays verified historical pieces with era provenance badges, current prices, and instant item links.
- **Active Promotional Banner:** Alerts visitors to ongoing category discount events (e.g., *15% off Coins & Numismatics*).

### 2.2 Marketplace Catalog (`/catalog/marketplace/`)
- **Faceted Search Sidebar:**
  - **Keyword Search:** Real-time search matching item code/SKU, title, geographical origin, and description.
  - **Category & SubCategory:** Filter by specific historical eras or artifact mediums.
  - **Price Range Filter:** Input Minimum (₹) and Maximum (₹) thresholds.
  - **Age Range Filter:** Filter artifacts by age (e.g., items over 500 years old).
  - **Sorting Options:** *Newest Arrivals*, *Price: Low to High*, *Price: High to Low*, *Oldest Historical Age*.
- **Card Badges:** Displays real-time stock indicators (*Available*, *Low Stock: 2 Left*, *Out of Stock*), promotional discount tags, and geographical origin tags.

### 2.3 Product Detail Page (`/catalog/items/<item_id>/`)
- **Artifact Visuals:** High-resolution image viewport with thumbnail selector for secondary and hallmark photographs. Clicking opens a full-screen zoom preview.
- **Provenance Data Sheet:** Displays registered age in years, historical era, cultural origin, seller shop information, and curator condition report.
- **Interactive Actions:**
  - Authenticated buyers see an *"Add to Cart"* quantity selector and an *"Add to Watchlist"* heart toggle.
  - Sellers viewing their own listings see an *"Edit Listing"* button instead of purchase controls.

### 2.4 FAQ Knowledge Base (`/community/faq/`)
- **Accordion Interface:** Bootstrap 5 collapsible accordion categorized into *Authenticity*, *Shipping*, *Payments*, *Returns*, and *Selling*.
- **Real-Time Search:** Client-side filter box that instantly highlights matching questions and answers as the user types.

---

## 3. Buyer User Manual

### 3.1 Registration & Authentication (`/accounts/register/`, `/accounts/login/`)
1. Click **Sign In** on the navbar, then select **Register as Buyer**.
2. Provide a unique username, full name, 10-digit Indian mobile number (`^[6-9]\d{9}$`), email address, password, and street address.
3. Select your **State**; the **District** dropdown automatically updates via AJAX. Selecting a district updates the **Location** dropdown.
4. Submit the form. Buyer accounts are initialized with `status='Active'` immediately.

### 3.2 Managing the Watchlist (`/community/watchlist/`)
1. While browsing the catalog or inspecting an item, click the **Heart Icon** to add/remove the artifact.
2. Navigate to **My Watchlist** via the user dropdown menu.
3. Review saved items, current stock availability, and discounted prices.
4. Click **Move to Cart** to transfer the item directly to the shopping cart.

### 3.3 Shopping Cart Operations (`/orders/cart/`)
1. Navigate to **Cart** via the navbar icon.
2. Review line items, individual prices, category discounts saved, and subtotal.
3. **Quantity Adjustment:** Change the quantity input and click **Update**. The system prevents selecting quantities above available stock.
4. **Remove Item:** Click the trash icon; a confirmation modal prevents accidental deletions (DFD 1.2.1).
5. **Shipping Logic:** Shipping is automatically calculated (₹250 flat fee; **FREE** for orders exceeding ₹50,000).
6. Click **Proceed to Checkout**.

### 3.4 Order Confirmation & Stock Reservation (`/orders/checkout/confirm/`)
1. The checkout page displays the delivery address, order item breakdown, and grand total.
2. Click **Confirm Order**.
3. **Database Action:** An atomic transaction creates a `PurchaseMaster` record (`status='Pending'`, `pay_status='Unpaid'`), records line items in `Purchase`, reserves the inventory by decrementing `cur_stock`, and wipes the buyer's cart.

### 3.5 PCI-DSS Compliant Demo Card Payment (`/payments/<order_id>/checkout/`)
1. Choose payment mode: **Credit / Debit Card** or **Cash on Delivery (COD)**.
2. For Card Payments, enter:
   - **Cardholder Name:** Full name as printed on card.
   - **Card Method:** Credit Card or Debit Card.
   - **Card Number:** Enter a test card (e.g., `4111 1111 1111 1111`). The Luhn algorithm verifies the Mod-10 checksum in real time.
   - **Expiry Date:** Select Month (01–12) and Year (must be current or future year).
   - **CVV:** Enter 3 or 4 digits.
   - **Issuing Bank:** Select from the Indian banking partners dropdown (SBI, HDFC, ICICI, etc.).
3. Click **Authorize & Pay Securely**.
4. **Security Verification:** The system records only the last 4 digits (`4111`), card type (`Visa`), issuing bank, and transaction ID (`TXN-AH-...`). The full PAN and CVV are discarded. Order status advances to `Confirmed` and `Paid`.

### 3.6 Printable Tax Invoice & Payment Receipt (`/payments/<order_id>/receipt/`)
1. Upon successful payment, the buyer is redirected to the official Tax Invoice page.
2. The page displays the seller details, buyer address, itemized breakdown, GST breakdown, payment reference, and a bold green **PAID** rubber-stamp.
3. Click **Print / Save as PDF**. The page includes dedicated `@media print` CSS that automatically hides navigation bars, buttons, and backgrounds for an official, clean paper receipt.

### 3.7 Order Tracking & Cancellation (`/orders/my-orders/`, `/orders/<order_id>/`)
1. Navigate to **My Orders** to inspect past purchases.
2. Click **Track Order Status** to view the live status timeline:  
   `Pending` $\rightarrow$ `Confirmed` $\rightarrow$ `Shipped` $\rightarrow$ `Delivered`.
3. **Cancellation:** If the order is still in `Pending` or `Confirmed` state (not yet shipped), the buyer can click **Cancel Order**. Cancelling automatically restores the stock back to the inventory ledger.

### 3.8 Verified Buyer Comments & Reviews (`/community/items/<item_id>/comment/`)
1. On an item detail page, scroll down to **Collector Reviews**.
2. If you have purchased the item, a **Verified Buyer** badge is assigned to your account.
3. Select a rating from **1 to 5 Stars** and write your review.
4. Input is sanitized to prevent XSS script injections, and any prohibited words are masked automatically (e.g. `s***`, `i****`).

---

## 4. Seller User Manual

### 4.1 Seller Onboarding (`/accounts/register/`)
1. Register with role **Seller**, selecting your workshop/shop location and contact details.
2. Account is initially created with `status='Pending'`.
3. An administrative notification confirms: *"Your seller application is under review by the Administrator."*
4. Once approved by the Admin, the seller can log in to the Seller Portal.

### 4.2 Uploading an Antique Listing (`/catalog/seller/items/upload/`)
1. In the Seller Hub, click **Upload New Artifact**.
2. Enter the **Item SKU / Reference Code** (e.g. `CHOLA-BELL-1200`).
3. Enter the **Title**, select **Category** and cascading **SubCategory**.
4. Enter the **Historical Age** in years (e.g. `850`) and **Geographical Origin** (e.g. `Thanjavur, Chola Dynasty`).
5. Provide a detailed **Provenance & Condition Description**.
6. Upload high-resolution photographs: Primary Image, Secondary Hallmark, and Detail View. The client-side image preview renders thumbnails instantly before submission.
7. Set the **Selling Price (₹)** and **Initial Stock Quantity**.
8. Click **Publish Antique Listing**. Both the `Item` record and opening `Stock` ledger entry are created simultaneously.

### 4.3 Inventory & Stock Management (`/inventory/seller/stock/`)
1. Navigate to **Stock Management**.
2. The table displays every listing with **Total Arrived Stock**, **Current Available Stock**, and real-time status.
3. Listings with 1 or 2 units remaining are highlighted with an amber **Low Stock** badge.
4. Click **+ Add Stock** on any item, enter the newly arrived quantity, and submit. The system updates both `tot_arr_stock` and `cur_stock` with an updated timestamp.

### 4.4 Managing Listings (`/catalog/seller/items/`)
1. Click **My Listings** to inspect catalog items.
2. Click **Edit** to modify pricing, description, or photographs. (Security check: Sellers can only edit their own items; editing another seller's item raises HTTP 403).
3. Click **Delete** to retire an item with confirmation.

### 4.5 Viewing Seller Orders (`/orders/seller-orders/`)
1. Click **Orders Received** in the seller menu.
2. The table displays customer orders containing your items, quantity ordered, buyer shipping address, and payment status.

---

## 5. Administrator User Manual

### 5.1 Master Analytics Dashboard (`/dashboard/admin/`)
1. Log in with administrator credentials (`admin` / `AdminPass123!`).
2. **Key Metric Cards:**
   - **Total Registered Users** (with breakdown of buyers vs sellers).
   - **Active Antique Listings** & Total Catalog Value.
   - **Completed Orders** & Total Platform Revenue (GMV).
   - **Pending Seller Applications** requiring attention.
3. **Interactive Visualizations (Chart.js):**
   - **Monthly Revenue Trend:** Interactive line/bar chart displaying revenue across months.
   - **Category Distribution:** Doughnut chart showing the proportion of items listed per category.

### 5.2 Seller Verification & Activation (`/dashboard/admin/`)
1. The dashboard features a dedicated **Pending Seller Verification Queue**.
2. Inspect the seller's business name, registered location, phone, and email.
3. Click **Activate** to grant immediate portal access. The seller receives immediate access to upload listings.
4. Click **Deactivate / Suspend** at any time to freeze seller privileges.

### 5.3 User Management (`/dashboard/admin/users/`)
1. Navigate to **Manage Users**.
2. Filter users by role (*All*, *Admin*, *Seller*, *Buyer*) or search by username/email.
3. Click **Block / Unblock** to toggle account access in real time. Blocked users are immediately prevented from logging in.

### 5.4 Category & SubCategory CRUD (`/catalog/categories/`, `/catalog/subcategories/`)
1. Navigate to **Manage Categories**.
2. Add new antique categories or edit existing definitions.
3. **Integrity Protection:** The system prevents deleting any category or subcategory that currently has active antique items attached, preventing accidental orphaned database rows.

### 5.5 Promotional Discounts Management (`/inventory/admin/discounts/`)
1. Navigate to **Item Discounts**.
2. Click **Add New Discount**.
3. Select an applicable category (or leave blank for platform-wide discount), enter a percentage (1% to 90%), and select Start and End dates.
4. **Validation:** End date must be strictly after the start date.
5. The discount automatically applies uniformly across all catalog items in that category and expires automatically after the end date.

### 5.6 Master Audit Reports Hub (`/dashboard/admin/reports/`)
The Reports Hub provides 6 comprehensive audit ledgers with custom date filtering and instant **CSV** or **PDF** export:

| Report Name | Route | Export Formats | Report Contents |
|---|---|---|---|
| **Users Audit Report** | `/dashboard/admin/reports/users/` | CSV & PDF | All registered users, roles, phone, locations, registration date, status |
| **Catalog Items Report** | `/dashboard/admin/reports/items/` | CSV & PDF | SKU, title, category, seller, price, stock, origin, listing date |
| **Orders Master Report** | `/dashboard/admin/reports/orders/` | CSV & PDF | Order ID, buyer, items count, total amount, order date, order status, payment status |
| **Sales & Revenue Report** | `/dashboard/admin/reports/sales/` | CSV & PDF | Paid transactions, seller breakdown, order revenue, net platform sales |
| **Payments Audit Ledger** | `/dashboard/admin/reports/payments/` | CSV & PDF | Transaction reference ID, masked card digits, bank, payment method, amount, status |
| **Inventory & Stock Report**| `/dashboard/admin/reports/stock/` | CSV & PDF | Item name, seller, total arrived stock, current stock, low stock warning indicators |

---

## 6. Visual Interface Verification Checklist

Quality assurance teams, operators, and stakeholders can verify the user experience against the following 25 interface checkpoints:

| Screen ID | Role | Page Name | URL Route | Key Visual Elements to Capture |
|---|---|---|---|---|
| **SCR-01** | Public | Landing Page (Hero) | `/` | Dark antique theme, gold navigation bar, hero CTA buttons, Cinzel font |
| **SCR-02** | Public | Featured Items Section | `/` | Product cards with prices, provenance badges, and promotional discount tags |
| **SCR-03** | Public | Marketplace Search & Filters | `/catalog/marketplace/` | Search bar with keyword query, category pills, price range, and sorting dropdown |
| **SCR-04** | Public | Artifact Detail Page | `/catalog/items/1/` | Primary image, thumbnail gallery, provenance details, and Add to Cart box |
| **SCR-05** | Public | Searchable FAQ Accordion | `/community/faq/` | Accordion cards, active collapse view, and client-side search input |
| **SCR-06** | Auth | Common Login Form | `/accounts/login/` | Unified login card, username/password inputs, and role redirection notice |
| **SCR-07** | Auth | Buyer Registration Form | `/accounts/register/` | 10-digit phone validation, cascading State $\rightarrow$ District $\rightarrow$ Location dropdowns |
| **SCR-08** | Buyer | Shopping Cart Summary | `/orders/cart/` | Item totals, applied category discounts, free shipping badge, and checkout button |
| **SCR-09** | Buyer | Order Checkout Confirmation | `/orders/checkout/confirm/` | Delivery address breakdown, order summary, and atomic Confirm Order button |
| **SCR-10** | Buyer | Demo Card Payment Checkout | `/payments/1/checkout/` | Cardholder name, Luhn card number input, MM/YY expiry, CVV, and bank selector |
| **SCR-11** | Buyer | Printable Tax Invoice | `/payments/1/receipt/` | Green PAID rubber-stamp, transaction reference ID, and masked `**** 4111` card number |
| **SCR-12** | Buyer | My Orders & Status Timeline | `/orders/my-orders/` | List of orders with Confirmed/Shipped badges and Track Status timeline |
| **SCR-13** | Buyer | Watchlist Page | `/community/watchlist/` | Saved artifact cards, current price, and Move to Cart button |
| **SCR-14** | Buyer | Verified Customer Review | `/catalog/items/1/` | 5-star rating, verified buyer badge, and profanity masking demonstration |
| **SCR-15** | Seller | Seller Upload Form | `/catalog/seller/items/upload/` | Multi-image file input, instant image preview thumbnails, SKU, age, origin |
| **SCR-16** | Seller | My Listings Management | `/catalog/seller/items/` | Table of seller's items with Edit and Delete action buttons |
| **SCR-17** | Seller | Inventory Stock Ledger | `/inventory/seller/stock/` | Arrived stock vs current stock, low-stock warnings, and Add Stock modal |
| **SCR-18** | Seller | Seller Orders Console | `/orders/seller-orders/` | Orders received containing seller's items and fulfillment tracking |
| **SCR-19** | Admin | Admin Master Dashboard | `/dashboard/admin/` | 4 KPI metric cards, pending seller quick-action buttons, recent transactions |
| **SCR-20** | Admin | Chart.js Analytics | `/dashboard/admin/` | Monthly sales trend chart and category distribution doughnut chart |
| **SCR-21** | Admin | User Management Hub | `/dashboard/admin/users/` | User listing table, role badge filters, and Block/Unblock toggle buttons |
| **SCR-22** | Admin | Category & SubCategory CRUD | `/catalog/categories/` | Category list, Add Category modal, and child subcategory tree |
| **SCR-23** | Admin | Promotional Discounts Table | `/inventory/admin/discounts/` | Active discounts table with percentage, category, and date-range validity |
| **SCR-24** | Admin | Master Audit Reports Hub | `/dashboard/admin/reports/` | Directory of 6 reports with date-picker filters and CSV/PDF export buttons |
| **SCR-25** | System | Custom Error 404 Page | `/non-existent-url/` | Antique-themed 404 illustrated layout with Return Home button |
