"""
Test suite for Module 8 – Payments in Antique Hub.
Covers:
- Pluggable payment gateway service architecture & factory resolution
- Luhn algorithm (Mod-10) card validation (valid vs invalid cards)
- Expiration date validation (past, valid future, invalid months)
- CVV length checking and card network BIN detection (Visa, MasterCard, RuPay, Amex)
- Demo payment flow: Credit/Debit Card checkout with PCI-DSS compliance
  (stores ONLY last 4 digits, card brand, bank name, amount, date, and generated transaction ID)
- Never stores full PAN or CVV
- Cash on Delivery (COD) demo payment flow
- Order pay_status update from 'Unpaid' to 'Paid' and order fulfillment status update
- Printable Tax Invoice & Payment Receipt view (Buyer, participating Seller, Admin access)
- Access control: blocking unrelated buyers from paying or viewing other buyers' receipts
- Blocking payment for cancelled orders or already-paid orders
- Seller "View Payment and Order" ledger with date, status, and search filters + revenue metrics
- Admin "View Payment and Order" master audit ledger with date, status, method filters + platform GMV
"""

import io
from decimal import Decimal
from datetime import datetime, timedelta
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Role, UserProfile
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock
from locations.models import State, District, Location
from orders.models import PurchaseMaster, Purchase
from payments.models import Payment
from payments.services import (
    BasePaymentGateway,
    DemoPaymentGateway,
    RazorpayTestGateway,
    get_payment_gateway,
    PaymentResult
)


def create_test_image(filename='pay_test.jpg', size=(100, 100), color='gold'):
    """Helper to generate in-memory dummy image."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')


class Module8PaymentGatewayTests(TestCase):
    """
    Unit tests for the pluggable Gateway Service and algorithm validations.
    """

    def setUp(self):
        self.gateway = DemoPaymentGateway()

    def test_luhn_algorithm_valid_and_invalid_cards(self):
        """
        Tests the Luhn algorithm against known valid card numbers and invalid numbers.
        """
        # Valid test card numbers
        self.assertTrue(self.gateway.validate_luhn("4111 1111 1111 1111"))  # Visa
        self.assertTrue(self.gateway.validate_luhn("5555-5555-5555-4444"))  # MasterCard
        self.assertTrue(self.gateway.validate_luhn("6080123456789015"))      # RuPay (Sum = 60)
        self.assertTrue(self.gateway.validate_luhn("378282246310005"))       # Amex 15-digit

        # Invalid checksums
        self.assertFalse(self.gateway.validate_luhn("4111 1111 1111 1112"))
        self.assertFalse(self.gateway.validate_luhn("5555555555554445"))
        self.assertFalse(self.gateway.validate_luhn("1234567890123456"))
        self.assertFalse(self.gateway.validate_luhn("not-a-number"))
        self.assertFalse(self.gateway.validate_luhn("123"))

    def test_expiration_date_validation(self):
        """
        Tests expiration month and year rules.
        """
        now = datetime.now()
        current_year = now.year

        # Valid future dates
        valid, _ = self.gateway.validate_expiry("12", str(current_year + 2))
        self.assertTrue(valid)
        valid, _ = self.gateway.validate_expiry("06", str(current_year + 5))
        self.assertTrue(valid)
        valid, _ = self.gateway.validate_expiry("01", str((current_year + 2) % 100))  # 2-digit year
        self.assertTrue(valid)

        # Past dates
        valid, err = self.gateway.validate_expiry("01", str(current_year - 1))
        self.assertFalse(valid)
        self.assertIn("cannot be in the past", err)

        # Invalid month
        valid, err = self.gateway.validate_expiry("13", str(current_year + 1))
        self.assertFalse(valid)
        self.assertIn("between 1 and 12", err)

        # Non-numeric
        valid, err = self.gateway.validate_expiry("XX", "YYYY")
        self.assertFalse(valid)

    def test_card_type_detection(self):
        """
        Tests BIN-based detection for Visa, MasterCard, RuPay, and American Express.
        """
        self.assertEqual(self.gateway.detect_card_type("4111111111111111"), "Visa")
        self.assertEqual(self.gateway.detect_card_type("5200000000000000"), "MasterCard")
        self.assertEqual(self.gateway.detect_card_type("6080123456789010"), "RuPay")
        self.assertEqual(self.gateway.detect_card_type("378282246310005"), "American Express")

    def test_cvv_validation(self):
        """
        Tests CVV length requirements (3 digits for Visa, 4 digits for Amex).
        """
        valid, _ = self.gateway.validate_cvv("123", "Visa")
        self.assertTrue(valid)
        valid, _ = self.gateway.validate_cvv("8492", "American Express")
        self.assertTrue(valid)

        # Invalid length
        valid, _ = self.gateway.validate_cvv("12", "Visa")
        self.assertFalse(valid)
        valid, _ = self.gateway.validate_cvv("123", "American Express")
        self.assertFalse(valid)

        # Non-numeric
        valid, _ = self.gateway.validate_cvv("abc", "Visa")
        self.assertFalse(valid)

    @override_settings(PAYMENT_GATEWAY_CLASS='payments.services.RazorpayTestGateway')
    def test_replaceable_gateway_factory(self):
        """
        Tests that get_payment_gateway dynamically instantiates the class defined in settings.
        """
        gateway = get_payment_gateway()
        self.assertIsInstance(gateway, RazorpayTestGateway)
        self.assertIsInstance(gateway, BasePaymentGateway)


class Module8PaymentFlowIntegrationTests(TestCase):
    """
    End-to-end integration tests for payment checkout, invoice generation,
    seller payment views, admin master audit ledger, and security boundaries.
    """

    @classmethod
    def setUpTestData(cls):
        # Roles
        cls.admin_role, _ = Role.objects.get_or_create(role='Admin')
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        cls.buyer_role, _ = Role.objects.get_or_create(role='Buyer')

        # Location Hierarchy
        cls.state_kerala = State.objects.create(state='Kerala')
        cls.dist_ernakulam = District.objects.create(dist='Ernakulam', state=cls.state_kerala)
        cls.loc_fortkochi = Location.objects.create(locname='Fort Kochi Heritage Zone', district=cls.dist_ernakulam)

        # 1. Admin User
        cls.admin_user = User.objects.create_superuser(
            username='admin_pay',
            email='admin@pay.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_pay',
            contactname='Master Administrator',
            phone='9876543301',
            email='admin@pay.test',
            status='Active'
        )

        # 2. Seller 1 (Owner of Item 1)
        cls.seller1 = User.objects.create_user(
            username='seller1_pay',
            email='seller1@pay.test',
            password='SellerPassword123!'
        )
        cls.seller1_profile = UserProfile.objects.create(
            login=cls.seller1,
            role=cls.seller_role,
            username='seller1_pay',
            contactname='Malabar Antique Emporium',
            phone='9876543302',
            email='seller1@pay.test',
            address='12 Spice Route, Mattancherry',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_fortkochi,
            status='Active'
        )

        # 3. Seller 2 (Owner of Item 2)
        cls.seller2 = User.objects.create_user(
            username='seller2_pay',
            email='seller2@pay.test',
            password='SellerPassword123!'
        )
        cls.seller2_profile = UserProfile.objects.create(
            login=cls.seller2,
            role=cls.seller_role,
            username='seller2_pay',
            contactname='Deccan Antiquities',
            phone='9876543303',
            email='seller2@pay.test',
            status='Active'
        )

        # 4. Buyer 1 (Legitimate purchaser)
        cls.buyer1 = User.objects.create_user(
            username='buyer1_pay',
            email='buyer1@pay.test',
            password='BuyerPassword123!'
        )
        cls.buyer1_profile = UserProfile.objects.create(
            login=cls.buyer1,
            role=cls.buyer_role,
            username='buyer1_pay',
            contactname='Ramesh C. Verma',
            phone='9876543304',
            email='buyer1@pay.test',
            address='74 Heritage Manor',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_fortkochi,
            status='Active'
        )

        # 5. Buyer 2 (Unauthorized interloper)
        cls.buyer2 = User.objects.create_user(
            username='buyer2_pay',
            email='buyer2@pay.test',
            password='BuyerPassword123!'
        )
        cls.buyer2_profile = UserProfile.objects.create(
            login=cls.buyer2,
            role=cls.buyer_role,
            username='buyer2_pay',
            contactname='Stranger Buyer',
            phone='9876543305',
            email='buyer2@pay.test',
            status='Active'
        )

        # Category & SubCategory
        cls.cat_coins = Category.objects.create(category='Coins', description='Ancient coinage')
        cls.subcat_chola = SubCategory.objects.create(
            category=cls.cat_coins,
            subcategory='Chola Dynasty'
        )

        # Artifact 1 (Belongs to Seller 1)
        cls.item1 = Item.objects.create(
            item='COIN-101',
            title='10th Century Chola Gold Kahavanu',
            category=cls.cat_coins,
            subcategory=cls.subcat_chola,
            years_old=1020,
            origin='Thanjavur, Chola Empire',
            price=45000.00,
            status='Available',
            img1=create_test_image('coin1.jpg'),
            description='Rare Raja Raja Chola gold kahavanu.',
            seller=cls.seller1
        )
        cls.stock1 = Stock.objects.create(item=cls.item1, tot_arr_stock=5, cur_stock=5, status='In Stock')

        # Artifact 2 (Belongs to Seller 2)
        cls.item2 = Item.objects.create(
            item='COIN-102',
            title='Pandyan Dynasty Silver Coin',
            category=cls.cat_coins,
            subcategory=cls.subcat_chola,
            years_old=800,
            origin='Madurai',
            price=12000.00,
            status='Available',
            img1=create_test_image('coin2.jpg'),
            description='Pandyan silver coin with fish emblem.',
            seller=cls.seller2
        )
        cls.stock2 = Stock.objects.create(item=cls.item2, tot_arr_stock=3, cur_stock=3, status='In Stock')

    def setUp(self):
        self.client = Client()

    def test_card_payment_flow_pci_dss_compliance_and_order_update(self):
        """
        Buyer chooses Card payment, inputs valid card with Luhn check.
        Verifies:
        - Stores ONLY last 4 digits, card type, bank name, amount, date, transaction ID.
        - NEVER stores full card number or CVV.
        - Updates PurchaseMaster pay_status='Paid' and status='Confirmed'.
        - Redirects to printable receipt page.
        """
        # Create an unpaid order for Buyer 1
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('45250.00'),
            status='Pending',
            pay_status='Unpaid'
        )
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=1)

        self.client.login(username='buyer1_pay', password='BuyerPassword123!')

        # 1. Inspect checkout page GET
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})
        resp = self.client.get(checkout_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'payments/checkout.html')
        self.assertContains(resp, "45250.00")

        # 2. Submit valid Credit Card payment
        payload = {
            'payment_type': 'card',
            'card_holder': 'Ramesh C. Verma',
            'card_method': 'Credit Card',
            'card_number': '4111 1111 1111 1111',  # Valid Visa passing Luhn check
            'exp_month': '12',
            'exp_year': '2028',
            'cvv': '842',
            'bank_name': 'State Bank of India',
        }
        post_resp = self.client.post(checkout_url, payload)
        self.assertEqual(post_resp.status_code, 302)

        receipt_url = reverse('payments:receipt', kwargs={'order_id': order.purchaseid})
        self.assertRedirects(post_resp, receipt_url)

        # 3. Check Order status updated
        order.refresh_from_db()
        self.assertEqual(order.pay_status, 'Paid')
        self.assertEqual(order.status, 'Confirmed')

        # 4. Check Payment model storage (PCI-DSS validation)
        payment = Payment.objects.get(purchase_master=order)
        self.assertEqual(payment.amount, Decimal('45250.00'))
        self.assertEqual(payment.method, 'Credit Card')
        self.assertEqual(payment.status, 'Success')
        self.assertEqual(payment.card_last4, '1111')
        self.assertEqual(payment.card_type, 'Visa')
        self.assertEqual(payment.bank_name, 'State Bank of India')
        self.assertTrue(payment.transaction_ref.startswith('TXN-AH-'))

        # Verify that the full card number or CVV does NOT exist on the model
        self.assertFalse(hasattr(payment, 'card_number'))
        self.assertFalse(hasattr(payment, 'cvv'))

    def test_card_payment_fails_on_invalid_luhn_checksum(self):
        """
        Invalid card number failing Luhn algorithm re-renders form with clear error message
        without altering order or payment records.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Pending',
            pay_status='Unpaid'
        )

        self.client.login(username='buyer1_pay', password='BuyerPassword123!')
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})

        payload = {
            'payment_type': 'card',
            'card_holder': 'Ramesh C. Verma',
            'card_method': 'Credit Card',
            'card_number': '4111 1111 1111 1112',  # Invalid Luhn checksum
            'exp_month': '12',
            'exp_year': '2028',
            'cvv': '123',
            'bank_name': 'HDFC Bank',
        }
        resp = self.client.post(checkout_url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'payments/checkout.html')
        self.assertContains(resp, "Luhn algorithm checksum verification")

        order.refresh_from_db()
        self.assertEqual(order.pay_status, 'Unpaid')
        self.assertFalse(Payment.objects.filter(purchase_master=order).exists())

    def test_card_payment_fails_on_past_expiration_date(self):
        """
        Expired card date is rejected with an informative validation error.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Pending',
            pay_status='Unpaid'
        )

        self.client.login(username='buyer1_pay', password='BuyerPassword123!')
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})

        payload = {
            'payment_type': 'card',
            'card_holder': 'Ramesh C. Verma',
            'card_method': 'Credit Card',
            'card_number': '4111 1111 1111 1111',
            'exp_month': '01',
            'exp_year': '2022',  # Past year
            'cvv': '123',
            'bank_name': 'HDFC Bank',
        }
        resp = self.client.post(checkout_url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "cannot be in the past")

        order.refresh_from_db()
        self.assertEqual(order.pay_status, 'Unpaid')

    def test_cash_on_delivery_flow(self):
        """
        Buyer chooses Cash on Delivery (COD).
        Generates COD payment record with 'Cash on Delivery' method and marks pay_status='Paid'.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('12250.00'),
            status='Pending',
            pay_status='Unpaid'
        )
        Purchase.objects.create(purchase_master=order, item=self.item2, quantity=1)

        self.client.login(username='buyer1_pay', password='BuyerPassword123!')
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})

        payload = {
            'payment_type': 'cod',
        }
        resp = self.client.post(checkout_url, payload)
        self.assertEqual(resp.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.pay_status, 'Paid')

        payment = Payment.objects.get(purchase_master=order)
        self.assertEqual(payment.method, 'Cash on Delivery')
        self.assertIsNone(payment.card_last4)
        self.assertTrue(payment.transaction_ref.startswith('COD-AH-'))

    def test_printable_receipt_access_rules(self):
        """
        Printable receipt / invoice can be viewed by:
        - The Buyer who placed the order
        - The Admin
        - The Seller who curates items in the order
        Access is denied to an unrelated buyer.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Confirmed',
            pay_status='Paid'
        )
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=1)
        Payment.objects.create(
            buyer=self.buyer1,
            purchase_master=order,
            amount=order.tot_amt,
            method='Credit Card',
            status='Success',
            card_last4='1111',
            card_type='Visa',
            bank_name='State Bank of India',
            transaction_ref='TXN-AH-TEST-0001'
        )

        receipt_url = reverse('payments:receipt', kwargs={'order_id': order.purchaseid})

        # 1. Buyer 1 can view
        self.client.login(username='buyer1_pay', password='BuyerPassword123!')
        resp_b1 = self.client.get(receipt_url)
        self.assertEqual(resp_b1.status_code, 200)
        self.assertTemplateUsed(resp_b1, 'payments/receipt.html')
        self.assertContains(resp_b1, "TXN-AH-TEST-0001")
        self.assertContains(resp_b1, "PAID")

        # 2. Admin can view
        self.client.login(username='admin_pay', password='AdminPassword123!')
        resp_adm = self.client.get(receipt_url)
        self.assertEqual(resp_adm.status_code, 200)

        # 3. Seller 1 (owns item1) can view
        self.client.login(username='seller1_pay', password='SellerPassword123!')
        resp_s1 = self.client.get(receipt_url)
        self.assertEqual(resp_s1.status_code, 200)

        # 4. Unrelated Buyer 2 is blocked
        self.client.login(username='buyer2_pay', password='BuyerPassword123!')
        resp_b2 = self.client.get(receipt_url)
        self.assertEqual(resp_b2.status_code, 302)  # Redirects with permission error

    def test_stop_payment_on_cancelled_order(self):
        """
        Payment cannot be authorized on an order that has already been cancelled.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Cancelled',
            pay_status='Unpaid'
        )

        self.client.login(username='buyer1_pay', password='BuyerPassword123!')
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})
        resp = self.client.get(checkout_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('orders:order_detail', kwargs={'purchase_id': order.purchaseid}))

    def test_already_paid_order_redirects_to_receipt(self):
        """
        Attempting to access checkout for an already paid order redirects directly to receipt.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Confirmed',
            pay_status='Paid'
        )

        self.client.login(username='buyer1_pay', password='BuyerPassword123!')
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})
        resp = self.client.get(checkout_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('payments:receipt', kwargs={'order_id': order.purchaseid}))

    def test_seller_payments_view_filters_and_earnings(self):
        """
        Seller "View Payment and Order" displays only orders containing seller's items,
        correctly computes sales revenue, and supports status/date filters.
        """
        # Order 1: contains Seller 1 item (Item 1, ₹45,000) - Paid
        ord1 = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Confirmed',
            pay_status='Paid'
        )
        Purchase.objects.create(purchase_master=ord1, item=self.item1, quantity=1)
        Payment.objects.create(
            buyer=self.buyer1,
            purchase_master=ord1,
            amount=ord1.tot_amt,
            method='Credit Card',
            status='Success',
            card_last4='1111',
            card_type='Visa',
            bank_name='SBI',
            transaction_ref='TXN-AH-TEST-S1'
        )

        # Order 2: contains Seller 2 item only (Item 2, ₹12,000) - Paid
        ord2 = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('12250.00'),
            status='Confirmed',
            pay_status='Paid'
        )
        Purchase.objects.create(purchase_master=ord2, item=self.item2, quantity=1)

        # Login as Seller 1
        self.client.login(username='seller1_pay', password='SellerPassword123!')
        seller_orders_url = reverse('payments:seller_payments')
        resp = self.client.get(seller_orders_url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'payments/seller_payments.html')
        self.assertContains(resp, f"#{ord1.purchaseid}")
        self.assertNotContains(resp, f"#{ord2.purchaseid}")  # Seller 2 order must not appear
        self.assertEqual(resp.context['total_seller_earnings'], Decimal('45000.00'))

    def test_admin_payments_master_ledger_and_filters(self):
        """
        Admin "View Payment and Order" master audit ledger displays all platform orders,
        computes platform GMV, and supports multi-criteria filtering.
        """
        # Create paid order
        ord1 = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('45000.00'),
            status='Confirmed',
            pay_status='Paid'
        )
        Payment.objects.create(
            buyer=self.buyer1,
            purchase_master=ord1,
            amount=ord1.tot_amt,
            method='Credit Card',
            status='Success',
            card_last4='4242',
            card_type='Visa',
            bank_name='HDFC Bank',
            transaction_ref='TXN-AH-ADM-01'
        )

        # Create COD order
        ord2 = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('12250.00'),
            status='Confirmed',
            pay_status='Paid'
        )
        Payment.objects.create(
            buyer=self.buyer1,
            purchase_master=ord2,
            amount=ord2.tot_amt,
            method='Cash on Delivery',
            status='Success',
            bank_name='Courier Settlement',
            transaction_ref='COD-AH-ADM-02'
        )

        # Login as Admin
        self.client.login(username='admin_pay', password='AdminPassword123!')
        admin_pay_url = reverse('payments:admin_payments')
        resp = self.client.get(admin_pay_url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'payments/admin_payments.html')
        self.assertEqual(resp.context['total_paid_count'], 2)
        self.assertEqual(resp.context['total_paid_volume'], Decimal('57250.00'))  # 45000 + 12250
        self.assertEqual(resp.context['cod_orders_count'], 1)

        # Test filter by method = 'Cash on Delivery'
        resp_cod = self.client.get(admin_pay_url, {'method': 'Cash on Delivery'})
        self.assertEqual(resp_cod.status_code, 200)
        self.assertContains(resp_cod, "COD-AH-ADM-02")
        self.assertNotContains(resp_cod, "TXN-AH-ADM-01")
