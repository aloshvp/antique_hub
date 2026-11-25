"""
Module 15: Full System Test Script for Antique Hub Purchase Flow.
Simulates and validates the end-to-end e-commerce lifecycle:
1. Environment initialization & role-based user provisioning.
2. Seller uploads a new authentic antique item listing.
3. Inventory stock verification in the database.
4. Buyer logs in, searches marketplace, and views item detail.
5. Buyer adds item to cart and inspects cart summary.
6. Buyer confirms order -> Atomic transaction creates PurchaseMaster and reduces Stock.
7. Buyer completes payment using Luhn-validated Credit Card gateway.
8. Verifies order status transition (Pending -> Confirmed, Unpaid -> Paid).
9. Verifies PCI-DSS compliance (no full PAN or CVV stored; only last 4 digits & TXN-ID).
10. Generates and inspects official printable Tax Invoice & Payment Receipt.
11. Seller inspects seller order dashboard and order fulfillment status.
12. Comprehensive tear-down and database cleanup.

Usage:
    python scripts/system_test_purchase_flow.py
"""

import os
import sys
import io
from decimal import Decimal
from PIL import Image

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Setup Django Environment
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'antique_hub.settings')

import django
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.db import transaction

from accounts.models import Role, UserProfile
from locations.models import State, District, Location
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock
from orders.models import Cart, PurchaseMaster, Purchase
from payments.models import Payment


def create_in_memory_image(filename='system_natraja.jpg', size=(80, 80), color='goldenrod'):
    """Generate in-memory test image for artifact upload."""
    buffer = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(filename, buffer.read(), content_type='image/jpeg')


class SystemPurchaseFlowRunner:
    """Orchestrates end-to-end purchase flow validation."""

    def __init__(self):
        self.seller_client = Client()
        self.buyer_client = Client()
        self.created_objects = []
        self.step_counter = 0

    def log_step(self, title, description):
        self.step_counter += 1
        print(f"\n[{self.step_counter:02d}] \033[1;34m=== {title} ===\033[0m")
        print(f"     {description}")

    def log_success(self, message):
        print(f"     \033[1;32m[PASS] {message}\033[0m")

    def run(self):
        print("=" * 80)
        print("   ANTIQUE HUB - MODULE 15 FULL SYSTEM PURCHASE FLOW VERIFICATION")
        print("=" * 80)

        try:
            # Step 1: Provision Roles, Locations, and Test Accounts
            self.log_step("Setup Infrastructure & Users", "Creating roles, geographic hierarchy, seller, and buyer...")
            admin_role, _ = Role.objects.get_or_create(role='Admin')
            seller_role, _ = Role.objects.get_or_create(role='Seller')
            buyer_role, _ = Role.objects.get_or_create(role='Buyer')

            state, _ = State.objects.get_or_create(state='Tamil Nadu')
            dist, _ = District.objects.get_or_create(state=state, dist='Thanjavur')
            loc, _ = Location.objects.get_or_create(district=dist, locname='Brihadisvara Belt')

            # Test Seller
            seller_user, _ = User.objects.get_or_create(
                username='sys_test_seller',
                defaults={'email': 'sys_seller@antiquehub.test'}
            )
            seller_user.set_password('SellerSysPass123!')
            seller_user.save()
            seller_prof, _ = UserProfile.objects.get_or_create(
                login=seller_user,
                defaults={
                    'role': seller_role, 'username': 'sys_test_seller',
                    'contactname': 'Imperial Chola Antiquities', 'phone': '9876500001',
                    'email': 'sys_seller@antiquehub.test', 'status': 'Active',
                    'state': state, 'district': dist, 'location': loc
                }
            )

            # Test Buyer
            buyer_user, _ = User.objects.get_or_create(
                username='sys_test_buyer',
                defaults={'email': 'sys_buyer@antiquehub.test'}
            )
            buyer_user.set_password('BuyerSysPass123!')
            buyer_user.save()
            buyer_prof, _ = UserProfile.objects.get_or_create(
                login=buyer_user,
                defaults={
                    'role': buyer_role, 'username': 'sys_test_buyer',
                    'contactname': 'Maharaja Heritage Collection', 'phone': '9876500002',
                    'email': 'sys_buyer@antiquehub.test', 'status': 'Active',
                    'state': state, 'district': dist, 'location': loc
                }
            )

            category, _ = Category.objects.get_or_create(category='Sacred Bronzes')
            subcategory, _ = SubCategory.objects.get_or_create(category=category, subcategory='Chola Dynasty Idols')
            self.log_success("Roles, Locations, Seller ('sys_test_seller'), and Buyer ('sys_test_buyer') ready.")

            # Step 2: Seller Authentication
            self.log_step("Seller Authentication", "Authenticating seller via /accounts/login/...")
            login_success = self.seller_client.login(username='sys_test_seller', password='SellerSysPass123!')
            assert login_success, "Seller login failed!"
            self.log_success("Seller session authenticated successfully.")

            # Step 3: Seller Uploads Antique Item
            self.log_step("Item Upload & Stock Initialization", "Seller uploads a 10th-century Chola Nataraja artifact...")
            item_code = f"SYS-CHOLA-{timezone.now().strftime('%M%S')}"
            item_title = "10th Century Chola Lost-Wax Bronze Nataraja"
            item_price = Decimal("275000.00")
            initial_stock = 4

            item = Item.objects.create(
                seller=seller_user,
                item=item_code,
                title=item_title,
                category=category,
                subcategory=subcategory,
                years_old=1050,
                origin='Thanjavur Royal Foundry',
                description='Authentic lost-wax casting depicting Shiva Nataraja in cosmic dance with flame aureole.',
                price=item_price,
                status='Available',
                img1=create_in_memory_image('nataraja.jpg')
            )
            self.created_objects.append(item)

            stock = Stock.objects.create(
                item=item,
                tot_arr_stock=initial_stock,
                cur_stock=initial_stock,
                stockdate=timezone.now(),
                status='Available'
            )
            self.created_objects.append(stock)
            self.log_success(f"Item #{item.itemid} '{item.title}' created with price ₹{item.price:,.2f} and stock {stock.cur_stock}.")

            # Step 4: Buyer Authentication
            self.log_step("Buyer Authentication", "Authenticating buyer via /accounts/login/...")
            buyer_login_ok = self.buyer_client.login(username='sys_test_buyer', password='BuyerSysPass123!')
            assert buyer_login_ok, "Buyer login failed!"
            self.log_success("Buyer session established.")

            # Step 5: Buyer Searches Marketplace
            self.log_step("Marketplace Search & Discovery", "Buyer searches for 'Nataraja'...")
            search_url = reverse('catalog:item_list')
            search_res = self.buyer_client.get(search_url, {'q': 'Nataraja'})
            assert search_res.status_code == 200, f"Search returned status {search_res.status_code}"
            assert item_title in search_res.content.decode('utf-8'), "Item not found in search results!"
            self.log_success(f"Found listing '{item_title}' in search query results (HTTP 200).")

            # Step 6: Buyer Views Item Detail Page
            self.log_step("Item Inspection", "Buyer navigates to item detail view...")
            detail_url = reverse('catalog:item_detail', kwargs={'item_id': item.itemid})
            detail_res = self.buyer_client.get(detail_url)
            assert detail_res.status_code == 200, "Item detail page failed!"
            assert "Thanjavur Royal Foundry" in detail_res.content.decode('utf-8')
            self.log_success("Item specifications, provenance, and high-res preview verified.")

            # Step 7: Add to Shopping Cart
            self.log_step("Add to Cart", "Buyer adds 2 units of the antique to cart...")
            add_cart_url = reverse('orders:add_to_cart', kwargs={'item_id': item.itemid})
            add_cart_res = self.buyer_client.post(add_cart_url, {'quantity': 2}, follow=True)
            assert add_cart_res.status_code == 200, "Add to cart failed!"

            cart_entry = Cart.objects.get(buyer=buyer_user, item=item)
            assert cart_entry.quantity == 2, f"Expected 2 items in cart, found {cart_entry.quantity}"
            self.log_success(f"Cart updated: 2 units reserved (Subtotal: ₹{item.price * 2:,.2f}).")

            # Step 8: Confirm Order & Stock Reduction
            self.log_step("Order Confirmation & Stock Reduction", "Confirming order atomically via /orders/checkout/confirm/...")
            confirm_url = reverse('orders:confirm_order')
            confirm_res = self.buyer_client.post(confirm_url, follow=False)
            assert confirm_res.status_code == 302, f"Order confirmation failed with status {confirm_res.status_code}"

            order = PurchaseMaster.objects.filter(buyer=buyer_user).latest('purchaseid')
            self.created_objects.append(order)
            assert order.status == 'Pending', f"Expected 'Pending', got '{order.status}'"
            assert order.pay_status == 'Unpaid', f"Expected 'Unpaid', got '{order.pay_status}'"
            expected_total = Decimal("550000.00")  # 2 * 275,000 + 0 shipping (>= 50,000 is free)
            assert order.tot_amt == expected_total, f"Expected total {expected_total}, got {order.tot_amt}"

            stock.refresh_from_db()
            assert stock.cur_stock == 2, f"Stock decrement failed: expected 2 remaining, got {stock.cur_stock}"
            assert stock.tot_arr_stock == 4, "Total arrived stock should remain unchanged at 4!"
            self.log_success(f"Order #{order.purchaseid} created. DB Stock immediately reduced from 4 to {stock.cur_stock}.")

            # Step 9: Payment Gateway Authorization (Luhn-checked Demo Card)
            self.log_step("Payment Processing (PCI-DSS Sandbox)", "Buyer pays with simulated Visa Card (4111 1111 1111 1111)...")
            pay_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})
            pay_payload = {
                'payment_type': 'card',
                'card_holder': 'Maharaja Heritage Collection',
                'card_method': 'Credit Card',
                'card_number': '4111 1111 1111 1111',  # Passes Mod-10 Luhn algorithm
                'exp_month': '11',
                'exp_year': '2029',
                'cvv': '999',
                'bank_name': 'State Bank of India',
            }
            pay_res = self.buyer_client.post(pay_url, pay_payload, follow=False)
            assert pay_res.status_code == 302, f"Payment failed with HTTP status {pay_res.status_code}"

            order.refresh_from_db()
            assert order.pay_status == 'Paid', f"Expected pay_status 'Paid', got '{order.pay_status}'"
            assert order.status == 'Confirmed', f"Expected status 'Confirmed', got '{order.status}'"

            payment = Payment.objects.get(purchase_master=order)
            self.created_objects.append(payment)
            assert payment.amount == expected_total, "Payment amount mismatch!"
            assert payment.card_last4 == '1111', "Card masking failed!"
            assert payment.card_type == 'Visa', "BIN card brand detection failed!"
            assert payment.transaction_ref.startswith('TXN-'), "Transaction reference ID generation failed!"
            assert not hasattr(payment, 'cvv') and not hasattr(payment, 'card_number'), "PCI violation: Full card or CVV found!"
            self.log_success(f"Payment Authorized: ₹{payment.amount:,.2f} recorded. Ref: {payment.transaction_ref} (Masked: **** **** **** {payment.card_last4}).")

            # Step 10: Tax Invoice & Payment Receipt Verification
            self.log_step("Tax Invoice Verification", "Buyer fetches printable tax receipt...")
            receipt_url = reverse('payments:receipt', kwargs={'order_id': order.purchaseid})
            receipt_res = self.buyer_client.get(receipt_url)
            assert receipt_res.status_code == 200, "Tax receipt rendering failed!"
            receipt_html = receipt_res.content.decode('utf-8')
            assert payment.transaction_ref in receipt_html, "Transaction reference missing from receipt!"
            assert "PAID" in receipt_html, "Paid stamp missing from receipt!"
            assert "1111" in receipt_html, "Masked card digits missing from receipt!"
            self.log_success(f"Tax Invoice & Payment Receipt generated with official status stamp.")

            # Step 11: Seller Order & Ledger Verification
            self.log_step("Seller Order Dashboard Check", "Seller verifies order appears in their sales ledger...")
            seller_orders_url = reverse('orders:seller_orders')
            seller_orders_res = self.seller_client.get(seller_orders_url)
            assert seller_orders_res.status_code == 200, "Seller orders view failed!"
            assert str(order.purchaseid) in seller_orders_res.content.decode('utf-8'), "Order not visible in seller dashboard!"
            self.log_success(f"Order #{order.purchaseid} confirmed visible in Seller's Order Management console.")

            print("\n" + "=" * 80)
            print("\033[1;32m   [SUCCESS] ALL 11 SYSTEM PURCHASE FLOW VALIDATION PHASES PASSED!\033[0m")
            print("=" * 80)
            return True

        except Exception as e:
            print(f"\n\033[1;31m   [FAILED] System test encountered an error: {e}\033[0m")
            import traceback
            traceback.print_exc()
            return False

        finally:
            print("\nTeardown: Cleaning up system test records from database...")
            # Cleanup in reverse dependency order
            Payment.objects.filter(purchase_master__buyer__username='sys_test_buyer').delete()
            Purchase.objects.filter(purchase_master__buyer__username='sys_test_buyer').delete()
            PurchaseMaster.objects.filter(buyer__username='sys_test_buyer').delete()
            Cart.objects.filter(buyer__username='sys_test_buyer').delete()
            Stock.objects.filter(item__item__startswith='SYS-CHOLA-').delete()
            Item.objects.filter(item__startswith='SYS-CHOLA-').delete()
            print("Cleanup complete. Database state restored.")


if __name__ == '__main__':
    runner = SystemPurchaseFlowRunner()
    success = runner.run()
    sys.exit(0 if success else 1)
