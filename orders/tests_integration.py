"""
Module 15 – Integration Tests for Antique Hub.
Covers end-to-end multi-step user workflows:
1. Seller adds antique item -> Item appears in Buyer catalog, category filter, and keyword search.
2. Buyer adds item to cart -> Cart calculates totals & discounts -> Confirms order
   -> Atomic transaction locks row and reduces current stock -> Order set to Pending/Unpaid
   -> Buyer makes card payment via gateway (Luhn verified) -> Order status becomes Paid
   -> Payment transaction logged with masked digits -> Printable receipt verified
   -> Stock reduction verified in database.
"""

import io
from decimal import Decimal
from datetime import timedelta
from PIL import Image
from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Role, UserProfile
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock, Discount
from locations.models import State, District, Location
from orders.models import Cart, PurchaseMaster, Purchase
from payments.models import Payment


def create_test_image(filename='integration_item.jpg', size=(120, 120), color='gold'):
    """Helper to generate an in-memory test image."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')


class Module15IntegrationFlowTests(TestCase):
    """
    End-to-End Integration Tests validating cross-module workflows.
    """

    @classmethod
    def setUpTestData(cls):
        # 1. Setup Roles
        cls.admin_role = Role.objects.create(role='Admin')
        cls.seller_role = Role.objects.create(role='Seller')
        cls.buyer_role = Role.objects.create(role='Buyer')

        # 2. Setup Location Hierarchy
        cls.state = State.objects.create(state='Tamil Nadu')
        cls.district = District.objects.create(dist='Thanjavur', state=cls.state)
        cls.location = Location.objects.create(locname='Chola Heritage Belt', district=cls.district)

        # 3. Setup Categories
        cls.cat_bronze = Category.objects.create(category='Chola Bronzes')
        cls.subcat_idols = SubCategory.objects.create(category=cls.cat_bronze, subcategory='Sacred Idols')

        # 4. Create Admin User
        cls.admin_user = User.objects.create_superuser(
            username='admin_integ', email='admin@integ.test', password='AdminPass123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user, role=cls.admin_role, username='admin_integ',
            contactname='Super Admin', phone='9876543210', email='admin@integ.test',
            address='Admin Office', state=cls.state, district=cls.district, location=cls.location,
            status='Active'
        )

        # 5. Create Verified Active Seller
        cls.seller_user = User.objects.create_user(
            username='chola_dealer', email='seller@chola.test', password='SellerPass123!'
        )
        cls.seller_profile = UserProfile.objects.create(
            login=cls.seller_user, role=cls.seller_role, username='chola_dealer',
            contactname='Chola Antiques Dealership', phone='9876543211', email='seller@chola.test',
            address='Thanjavur Royal Palace Road', state=cls.state, district=cls.district, location=cls.location,
            status='Active'
        )

        # 6. Create Active Buyer
        cls.buyer_user = User.objects.create_user(
            username='collector_roy', email='roy@collector.test', password='BuyerPass123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user, role=cls.buyer_role, username='collector_roy',
            contactname='Roy Vintage Collector', phone='9876543212', email='roy@collector.test',
            address='Park Street Heritage Suite', state=cls.state, district=cls.district, location=cls.location,
            status='Active'
        )

    def test_workflow_1_seller_adds_item_appears_in_buyer_search(self):
        """
        Integration Flow 1:
        Seller uploads a new antique item with opening stock of 5.
        Verify item is saved, initial Stock row is created, and item immediately
        appears in Buyer catalogue, keyword search, and category browsing.
        """
        # Step 1: Seller logs in
        seller_client = Client()
        login_res = seller_client.post(reverse('accounts:login'), {
            'username': 'chola_dealer',
            'password': 'SellerPass123!'
        })
        self.assertEqual(login_res.status_code, 302)

        # Step 2: Seller uploads new antique item
        image1 = create_test_image('nataraja_statue_front.jpg')
        image2 = create_test_image('nataraja_statue_back.jpg')

        upload_res = seller_client.post(reverse('catalog:item_create'), {
            'item': 'CHOLA-NATARAJA-001',
            'title': '11th Century Chola Nataraja Bronze',
            'category': self.cat_bronze.catid,
            'subcategory': self.subcat_idols.subcatid,
            'years_old': 950,
            'origin': 'Thanjavur, Tamil Nadu',
            'description': 'Museum quality sacred lost-wax cast Chola bronze sculpture depicting Lord Nataraja.',
            'price': '450000.00',
            'opening_stock': 5,
            'status': 'Available',
            'img1': image1,
            'img2': image2,
        })
        self.assertEqual(upload_res.status_code, 302)

        # Verify Item in database
        item = Item.objects.get(item='CHOLA-NATARAJA-001')
        self.assertEqual(item.title, '11th Century Chola Nataraja Bronze')
        self.assertEqual(item.seller, self.seller_user)
        self.assertEqual(item.price, Decimal('450000.00'))

        # Verify Stock record automatically initialized
        stock_record = Stock.objects.get(item=item)
        self.assertEqual(stock_record.tot_arr_stock, 5)
        self.assertEqual(stock_record.cur_stock, 5)

        # Step 3: Buyer searches for the new item in marketplace
        buyer_client = Client()
        # Search by keyword
        search_res = buyer_client.get(reverse('catalog:item_list'), {'q': 'Nataraja'})
        self.assertEqual(search_res.status_code, 200)
        self.assertContains(search_res, '11th Century Chola Nataraja Bronze')
        self.assertContains(search_res, 'CHOLA-NATARAJA-001')

        # Filter by Category
        cat_res = buyer_client.get(reverse('catalog:item_list'), {'category_id': self.cat_bronze.catid})
        self.assertEqual(cat_res.status_code, 200)
        self.assertContains(cat_res, '11th Century Chola Nataraja Bronze')

        # Inspect item detail page
        detail_res = buyer_client.get(reverse('catalog:item_detail', kwargs={'item_id': item.itemid}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, '950 Years Old')
        self.assertContains(detail_res, '₹450000')
        self.assertContains(detail_res, 'Chola Antiques Dealership')

    def test_workflow_2_cart_to_order_to_stock_reduced_to_payment(self):
        """
        Integration Flow 2:
        1. Item exists with cur_stock = 4.
        2. Buyer logs in, adds quantity of 2 to cart.
        3. Cart calculates correct subtotal and order summary.
        4. Buyer confirms order -> Atomic transaction:
           - PurchaseMaster created (status=Pending, pay_status=Unpaid)
           - Purchase row created with snapshot price
           - Stock atomically locked and reduced (4 -> 2)
        5. Buyer completes Card payment via Luhn-validated checkout:
           - Payment record created with masked 4 digits & transaction ID
           - PurchaseMaster pay_status updated to 'Paid'
           - Status updated to 'Confirmed'
        6. Printable receipt verified.
        7. Stock remaining in DB verified as 2 (tot_arr_stock remains 4).
        """
        # Step 1: Create initial antique listing with 4 in stock
        img = create_test_image('mughal_dagger.jpg')
        item = Item.objects.create(
            seller=self.seller_user,
            item='MUGHAL-DAGGER-1680',
            title='17th Century Mughal Jade Hilt Dagger',
            category=self.cat_bronze,
            subcategory=self.subcat_idols,
            years_old=345,
            origin='Delhi, Mughal Empire',
            description='Fine damascened steel blade with mutton-fat jade pistol-grip hilt.',
            price=Decimal('120000.00'),
            status='Available',
            img1=img
        )
        Stock.objects.create(
            item=item,
            tot_arr_stock=4,
            cur_stock=4,
            stockdate=timezone.now(),
            status='Available'
        )

        # Step 2: Buyer logs in
        buyer_client = Client()
        buyer_client.login(username='collector_roy', password='BuyerPass123!')

        # Step 3: Add to Cart (qty 2)
        add_cart_res = buyer_client.post(reverse('orders:add_to_cart', kwargs={'item_id': item.itemid}), {
            'quantity': 2
        })
        self.assertEqual(add_cart_res.status_code, 302)

        # Verify Cart contents
        cart_entry = Cart.objects.get(buyer=self.buyer_user, item=item)
        self.assertEqual(cart_entry.quantity, 2)

        cart_view_res = buyer_client.get(reverse('orders:cart_view'))
        self.assertEqual(cart_view_res.status_code, 200)
        self.assertContains(cart_view_res, '17th Century Mughal Jade Hilt Dagger')
        self.assertContains(cart_view_res, '240000')  # 2 * 120,000

        # Step 4: Confirm Order
        confirm_res = buyer_client.post(reverse('orders:confirm_order'))
        self.assertEqual(confirm_res.status_code, 302)

        # Verify Order created
        order = PurchaseMaster.objects.filter(buyer=self.buyer_user).latest('purchaseid')
        self.assertEqual(order.status, 'Pending')
        self.assertEqual(order.pay_status, 'Unpaid')
        self.assertEqual(order.tot_amt, Decimal('240000.00'))  # Shipping is free for orders >= 50,000

        purchase_items = Purchase.objects.filter(purchase_master=order)
        self.assertEqual(purchase_items.count(), 1)
        self.assertEqual(purchase_items.first().quantity, 2)
        self.assertEqual(purchase_items.first().price, Decimal('120000.00'))

        # VERIFY STOCK REDUCTION IN DATABASE
        stock_after_order = Stock.objects.get(item=item)
        self.assertEqual(stock_after_order.tot_arr_stock, 4)  # Total arrived stock never decreases
        self.assertEqual(stock_after_order.cur_stock, 2)       # 4 - 2 = 2

        # Verify Cart is now cleared
        self.assertFalse(Cart.objects.filter(buyer=self.buyer_user).exists())

        # Step 5: Process Payment via Luhn-validated Demo Gateway
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})
        checkout_page = buyer_client.get(checkout_url)
        self.assertEqual(checkout_page.status_code, 200)

        # Post payment with valid Luhn Visa card: 4111 1111 1111 1111
        pay_res = buyer_client.post(checkout_url, {
            'payment_type': 'card',
            'card_holder': 'Roy Vintage Collector',
            'card_method': 'Credit Card',
            'card_number': '4111 1111 1111 1111',
            'exp_month': '12',
            'exp_year': '2028',
            'cvv': '789',
            'bank_name': 'State Bank of India',
        })
        self.assertEqual(pay_res.status_code, 302)

        # Verify Order Status Updated to Paid & Confirmed
        order.refresh_from_db()
        self.assertEqual(order.pay_status, 'Paid')
        self.assertEqual(order.status, 'Confirmed')

        # Verify Payment Record Created
        payment_record = Payment.objects.get(purchase_master=order)
        self.assertEqual(payment_record.amount, Decimal('240000.00'))
        self.assertEqual(payment_record.card_last4, '1111')
        self.assertEqual(payment_record.card_type, 'Visa')
        self.assertTrue(payment_record.transaction_ref.startswith('TXN-'))
        # Ensure full PAN and CVV are NEVER stored in Payment model
        self.assertFalse(hasattr(payment_record, 'card_number'))
        self.assertFalse(hasattr(payment_record, 'cvv'))

        # Step 6: Verify Printable Tax Invoice & Receipt
        receipt_res = buyer_client.get(reverse('payments:receipt', kwargs={'order_id': order.purchaseid}))
        self.assertEqual(receipt_res.status_code, 200)
        self.assertContains(receipt_res, 'Tax Invoice &amp; Payment Receipt')
        self.assertContains(receipt_res, '1111')
        self.assertContains(receipt_res, payment_record.transaction_ref)
        self.assertContains(receipt_res, 'PAID')

        # Step 7: Verify Order Status Timeline
        track_res = buyer_client.get(reverse('orders:order_detail', kwargs={'purchase_id': order.purchaseid}))
        self.assertEqual(track_res.status_code, 200)
        self.assertContains(track_res, 'Confirmed')
        self.assertContains(track_res, 'Paid')

        # Final DB Stock Check
        final_stock = Stock.objects.get(item=item)
        self.assertEqual(final_stock.cur_stock, 2)
