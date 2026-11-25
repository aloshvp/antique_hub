"""
Test suite for Module 7 – Cart and Orders.
Covers:
- Add to Cart, update quantity (enforcing current stock limit), remove with confirmation (DFD 1.2.1)
- Cart summary calculation (item totals, promotional category discounts, shipping charge, grand total)
- Business Rule: Stop a buyer/seller from buying their own listed item
- Confirm Order: atomic transaction, creating PurchaseMaster (status='Pending', pay_status='Unpaid')
  and Purchase rows, transactional stock reduction with row locking (DFD 1.3, 1.3.1)
- Insufficient stock handling and transaction rollback at checkout
- Buyer "My Orders" and "Track Order Status" page with status timeline
- Buyer order cancellation before shipment and automatic stock restoration
- Seller "View Orders" showing orders containing their items
- Admin Master Order Management (DFD 5.1 to 5.3: view all, activate/confirm, ship, deliver, cancel)
"""

import io
from PIL import Image
from decimal import Decimal
from datetime import timedelta
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


def create_test_image(filename='order_test.jpg', size=(100, 100), color='gold'):
    """Helper to generate in-memory dummy image."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')


class Module7CartAndOrdersTests(TestCase):
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

        # 1. Admin
        cls.admin_user = User.objects.create_superuser(
            username='admin_ord',
            email='admin@ord.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_ord',
            contactname='Master Administrator',
            phone='9876543201',
            email='admin@ord.test',
            status='Active'
        )

        # 2. Seller 1 (Owner of Item 1 & Item 2)
        cls.seller1 = User.objects.create_user(
            username='seller1_ord',
            email='seller1@ord.test',
            password='SellerPassword123!'
        )
        cls.seller1_profile = UserProfile.objects.create(
            login=cls.seller1,
            role=cls.seller_role,
            username='seller1_ord',
            contactname='Kochi Heritage Antiquarians',
            phone='9876543202',
            email='seller1@ord.test',
            address='10 Heritage Street',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_fortkochi,
            status='Active'
        )

        # 3. Seller 2 (Owner of Item 3)
        cls.seller2 = User.objects.create_user(
            username='seller2_ord',
            email='seller2@ord.test',
            password='SellerPassword123!'
        )
        cls.seller2_profile = UserProfile.objects.create(
            login=cls.seller2,
            role=cls.seller_role,
            username='seller2_ord',
            contactname='Malabar Antique Emporium',
            phone='9876543203',
            email='seller2@ord.test',
            status='Active'
        )

        # 4. Buyer 1 (Active Collector)
        cls.buyer1 = User.objects.create_user(
            username='buyer1_ord',
            email='buyer1@ord.test',
            password='BuyerPassword123!'
        )
        cls.buyer1_profile = UserProfile.objects.create(
            login=cls.buyer1,
            role=cls.buyer_role,
            username='buyer1_ord',
            contactname='Royal Connoisseur',
            phone='9876543204',
            email='buyer1@ord.test',
            address='42 Palace Avenue, Kochi',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_fortkochi,
            status='Active'
        )

        # 5. Buyer 2 (Second Collector)
        cls.buyer2 = User.objects.create_user(
            username='buyer2_ord',
            email='buyer2@ord.test',
            password='BuyerPassword123!'
        )
        cls.buyer2_profile = UserProfile.objects.create(
            login=cls.buyer2,
            role=cls.buyer_role,
            username='buyer2_ord',
            contactname='Vintage Enthusiast',
            phone='9876543205',
            email='buyer2@ord.test',
            status='Active'
        )

        # Categories
        cls.cat_coins = Category.objects.create(
            category='Coins & Numismatics',
            description='Imperial coins'
        )
        cls.cat_furniture = Category.objects.create(
            category='Heritage Furniture',
            description='Colonial furniture'
        )

        # Promotional Category Discount on Coins: 20% off active
        today = timezone.localdate()
        cls.discount = Discount.objects.create(
            applicable_cat=cls.cat_coins,
            discount_percent=20.00,
            startdate=today - timedelta(days=5),
            enddate=today + timedelta(days=10)
        )

        # Artifact 1: Gold Mohur (Price 50,000, 20% off = 40,000, Stock 5, Seller 1)
        cls.item1 = Item.objects.create(
            item='COIN-001',
            title='1707 Aurangzeb Gold Mohur',
            category=cls.cat_coins,
            years_old=319,
            origin='Shahjahanabad Mint',
            price=50000.00,
            status='Available',
            img1=create_test_image('mohur.jpg'),
            description='Pure gold coin.',
            seller=cls.seller1
        )
        cls.stock1 = Stock.objects.create(item=cls.item1, tot_arr_stock=5, cur_stock=5, status='In Stock')

        # Artifact 2: Silver Rupee (Price 10,000, 20% off = 8,000, Stock 2, Seller 1)
        cls.item2 = Item.objects.create(
            item='COIN-002',
            title='1835 William IV Silver Rupee',
            category=cls.cat_coins,
            years_old=191,
            origin='Calcutta Mint',
            price=10000.00,
            status='Available',
            img1=create_test_image('rupee.jpg'),
            description='Uniform silver rupee.',
            seller=cls.seller1
        )
        cls.stock2 = Stock.objects.create(item=cls.item2, tot_arr_stock=2, cur_stock=2, status='In Stock')

        # Artifact 3: Teakwood Chair (Price 25,000, No discount, Stock 1, Seller 2)
        cls.item3 = Item.objects.create(
            item='FURN-001',
            title='1890 Victorian Armchair',
            category=cls.cat_furniture,
            years_old=136,
            origin='Madras Presidency',
            price=25000.00,
            status='Available',
            img1=create_test_image('chair.jpg'),
            description='Rosewood armchair.',
            seller=cls.seller2
        )
        cls.stock3 = Stock.objects.create(item=cls.item3, tot_arr_stock=1, cur_stock=1, status='In Stock')

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Cart Management Tests
    # -------------------------------------------------------------
    def test_add_to_cart_success_and_quantity_increment(self):
        """
        Buyer can add an available item to cart. Adding again increments quantity.
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')

        # 1. Add 1 unit of item1
        resp = self.client.post(reverse('orders:add_to_cart', kwargs={'item_id': self.item1.itemid}), {'quantity': 1})
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('orders:cart_view'))

        cart_entry = Cart.objects.get(buyer=self.buyer1, item=self.item1)
        self.assertEqual(cart_entry.quantity, 1)

        # 2. Add 2 more units of item1
        self.client.post(reverse('orders:add_to_cart', kwargs={'item_id': self.item1.itemid}), {'quantity': 2})
        cart_entry.refresh_from_db()
        self.assertEqual(cart_entry.quantity, 3)

    def test_stop_buyer_from_buying_own_item(self):
        """
        Business Rule: A seller cannot add their own listing to cart.
        """
        self.client.login(username='seller1_ord', password='SellerPassword123!')
        resp = self.client.post(reverse('orders:add_to_cart', kwargs={'item_id': self.item1.itemid}), {'quantity': 1})
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('catalog:item_detail', kwargs={'item_id': self.item1.itemid}))
        self.assertFalse(Cart.objects.filter(buyer=self.seller1, item=self.item1).exists())

    def test_add_to_cart_cannot_exceed_available_stock(self):
        """
        Requested quantity cannot exceed currently available stock.
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        # item3 only has 1 in stock
        self.client.post(reverse('orders:add_to_cart', kwargs={'item_id': self.item3.itemid}), {'quantity': 5})
        cart_entry = Cart.objects.get(buyer=self.buyer1, item=self.item3)
        self.assertEqual(cart_entry.quantity, 1)  # Capped at available stock (1)

    def test_update_cart_quantity_enforces_stock_limit(self):
        """
        Updating quantity cannot exceed stock limit; setting to 0 removes entry.
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        cart_entry = Cart.objects.create(buyer=self.buyer1, item=self.item2, quantity=1)  # stock is 2

        # 1. Update to valid quantity 2
        update_url = reverse('orders:update_cart_quantity', kwargs={'cart_id': cart_entry.cartid})
        self.client.post(update_url, {'quantity': 2})
        cart_entry.refresh_from_db()
        self.assertEqual(cart_entry.quantity, 2)

        # 2. Attempt update to 5 (exceeds stock 2) -> rejected
        self.client.post(update_url, {'quantity': 5})
        cart_entry.refresh_from_db()
        self.assertEqual(cart_entry.quantity, 2)  # Unchanged

        # 3. Update to 0 -> deleted
        self.client.post(update_url, {'quantity': 0})
        self.assertFalse(Cart.objects.filter(pk=cart_entry.pk).exists())

    def test_remove_from_cart_with_confirmation_flow(self):
        """
        DFD 1.2.1: Remove from cart with confirmation.
        GET renders confirmation page; POST removes the item.
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        cart_entry = Cart.objects.create(buyer=self.buyer1, item=self.item1, quantity=1)

        remove_url = reverse('orders:remove_from_cart', kwargs={'cart_id': cart_entry.cartid})

        # GET confirmation page
        resp_get = self.client.get(remove_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'orders/cart_confirm_remove.html')
        self.assertContains(resp_get, '1707 Aurangzeb Gold Mohur')

        # POST deletion
        resp_post = self.client.post(remove_url)
        self.assertEqual(resp_post.status_code, 302)
        self.assertRedirects(resp_post, reverse('orders:cart_view'))
        self.assertFalse(Cart.objects.filter(pk=cart_entry.pk).exists())

    def test_cart_summary_calculation_and_discounts(self):
        """
        Verify:
        - item totals (original MRP)
        - promotional category discount savings
        - shipping charge rule (free for >= 50k, 250 below)
        - grand total
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        # Add item2 (Price 10k, discounted 20% = 8k, Qty 1) -> Subtotal = 8,000 (< 50,000 -> Ship = 250)
        Cart.objects.create(buyer=self.buyer1, item=self.item2, quantity=1)

        resp1 = self.client.get(reverse('orders:cart_view'))
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.context['items_total'], Decimal('10000.00'))
        self.assertEqual(resp1.context['discount_total'], Decimal('2000.00'))
        self.assertEqual(resp1.context['subtotal'], Decimal('8000.00'))
        self.assertEqual(resp1.context['shipping_charge'], Decimal('250.00'))
        self.assertEqual(resp1.context['grand_total'], Decimal('8250.00'))

        # Now add item1 (Price 50k, discounted 20% = 40k, Qty 1) -> Subtotal = 48,000 (< 50k)
        # If Qty 2 of item1: Subtotal = 8,000 + 80,000 = 88,000 (>= 50k -> Free Shipping)
        Cart.objects.create(buyer=self.buyer1, item=self.item1, quantity=2)

        resp2 = self.client.get(reverse('orders:cart_view'))
        self.assertEqual(resp2.context['subtotal'], Decimal('88000.00'))
        self.assertEqual(resp2.context['shipping_charge'], Decimal('0.00'))  # Free shipping
        self.assertEqual(resp2.context['grand_total'], Decimal('88000.00'))

    # -------------------------------------------------------------
    # 2. Confirm Order & Stock Reduction (DFD 1.3, 1.3.1)
    # -------------------------------------------------------------
    def test_confirm_order_atomic_transaction_and_stock_reduction(self):
        """
        Confirming order creates PurchaseMaster (Pending, Unpaid) and Purchase rows,
        clears cart, and atomically reduces inventory stock using select_for_update().
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        # Item 1: current stock is 5. Add 2 units to cart.
        Cart.objects.create(buyer=self.buyer1, item=self.item1, quantity=2)
        # Item 3: current stock is 1. Add 1 unit to cart.
        Cart.objects.create(buyer=self.buyer1, item=self.item3, quantity=1)

        confirm_url = reverse('orders:confirm_order')
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, 302)

        # Verify PurchaseMaster created
        order = PurchaseMaster.objects.filter(buyer=self.buyer1).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'Pending')
        self.assertEqual(order.pay_status, 'Unpaid')
        self.assertRedirects(response, reverse('orders:order_detail', kwargs={'purchase_id': order.purchaseid}))

        # Verify Purchase rows created
        self.assertEqual(order.order_items.count(), 2)

        # Verify Cart cleared
        self.assertEqual(Cart.objects.filter(buyer=self.buyer1).count(), 0)

        # Verify Stock Reduction (DFD 1.3.1)
        self.stock1.refresh_from_db()
        self.item1.refresh_from_db()
        self.assertEqual(self.stock1.cur_stock, 3)  # 5 - 2 = 3
        self.assertEqual(self.item1.status, 'Available')

        self.stock3.refresh_from_db()
        self.item3.refresh_from_db()
        self.assertEqual(self.stock3.cur_stock, 0)  # 1 - 1 = 0
        # Automatically transitioned to 'Out of Stock'
        self.assertEqual(self.item3.status, 'Out of Stock')

    def test_confirm_order_insufficient_stock_rollback(self):
        """
        If stock becomes insufficient at checkout time, atomic transaction rolls back,
        no order is created, and user is shown error.
        """
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        # Cart has 2 units of item2 (which has 2 in stock)
        Cart.objects.create(buyer=self.buyer1, item=self.item2, quantity=2)

        # Another buyer buys 1 unit first, leaving only 1 available
        Stock.reduce_stock(item_id=self.item2.itemid, quantity=1)

        # Buyer 1 attempts checkout for 2 units -> Insufficient stock error!
        response = self.client.post(reverse('orders:confirm_order'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('orders:cart_view'))

        # No order created
        self.assertFalse(PurchaseMaster.objects.filter(buyer=self.buyer1).exists())
        # Cart remains intact
        self.assertTrue(Cart.objects.filter(buyer=self.buyer1).exists())

    # -------------------------------------------------------------
    # 3. Buyer Orders & Tracking Page Tests
    # -------------------------------------------------------------
    def test_buyer_order_list_isolation(self):
        """
        Buyers only see their own orders in "My Orders".
        """
        # Create order for buyer1
        order1 = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('40000.00'),
            status='Pending'
        )
        Purchase.objects.create(purchase_master=order1, item=self.item1, quantity=1)

        # Create order for buyer2
        order2 = PurchaseMaster.objects.create(
            buyer=self.buyer2,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('25250.00'),
            status='Confirmed'
        )
        Purchase.objects.create(purchase_master=order2, item=self.item3, quantity=1)

        # Buyer 1 views "My Orders"
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        resp = self.client.get(reverse('orders:buyer_orders'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'orders/buyer_order_list.html')
        self.assertContains(resp, f'#{order1.purchaseid}')
        self.assertNotContains(resp, f'#{order2.purchaseid}')

    def test_order_detail_tracking_and_timeline(self):
        """
        Order detail displays status timeline, relics list, financial totals,
        and cancellation option before shipment.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('8250.00'),
            status='Confirmed',
            pay_status='Unpaid'
        )
        Purchase.objects.create(purchase_master=order, item=self.item2, quantity=1)

        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        response = self.client.get(reverse('orders:order_detail', kwargs={'purchase_id': order.purchaseid}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_detail.html')

        # Milestones in context
        self.assertEqual(response.context['current_step_index'], 1)  # Confirmed is index 1
        self.assertTrue(response.context['can_cancel'])  # Can cancel while Confirmed

        # Content assertions
        self.assertContains(response, f'ORDER #{order.purchaseid}')
        self.assertContains(response, '1835 William IV Silver Rupee')
        self.assertContains(response, '₹8250.00')
        self.assertContains(response, 'Cancel Order')

    def test_order_detail_unrelated_user_forbidden(self):
        """
        An unrelated buyer cannot view someone else's order (403 Forbidden).
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('40000.00'),
            status='Pending'
        )
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=1)

        self.client.login(username='buyer2_ord', password='BuyerPassword123!')
        response = self.client.get(reverse('orders:order_detail', kwargs={'purchase_id': order.purchaseid}))
        self.assertEqual(response.status_code, 403)

    # -------------------------------------------------------------
    # 4. Buyer Order Cancellation & Restocking Tests
    # -------------------------------------------------------------
    def test_buyer_cancel_order_restocks_items(self):
        """
        Buyer cancelling order before shipment marks it Cancelled and restocks items.
        """
        # Buyer 1 placed order for item3 (cur_stock was reduced to 0, status='Out of Stock')
        Stock.reduce_stock(item_id=self.item3.itemid, quantity=1)
        self.stock3.refresh_from_db()
        self.item3.refresh_from_db()
        self.assertEqual(self.stock3.cur_stock, 0)
        self.assertEqual(self.item3.status, 'Out of Stock')

        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('250.00'),
            tot_amt=Decimal('25250.00'),
            status='Confirmed'
        )
        Purchase.objects.create(purchase_master=order, item=self.item3, quantity=1)

        # Buyer 1 cancels order
        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        cancel_url = reverse('orders:cancel_order', kwargs={'purchase_id': order.purchaseid})
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, 302)

        # Order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'Cancelled')

        # Stock restored!
        self.stock3.refresh_from_db()
        self.item3.refresh_from_db()
        self.assertEqual(self.stock3.cur_stock, 1)
        self.assertEqual(self.item3.status, 'Available')  # Restored to Available

    def test_buyer_cannot_cancel_shipped_order(self):
        """
        Orders already shipped cannot be cancelled by buyer.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('40000.00'),
            status='Shipped'
        )
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=1)

        self.client.login(username='buyer1_ord', password='BuyerPassword123!')
        response = self.client.post(reverse('orders:cancel_order', kwargs={'purchase_id': order.purchaseid}))
        self.assertEqual(response.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, 'Shipped')  # Not cancelled

    # -------------------------------------------------------------
    # 5. Seller "View Orders" Tests
    # -------------------------------------------------------------
    def test_seller_views_orders_containing_their_items(self):
        """
        Seller 1 sees orders containing items listed by Seller 1, but not Seller 2.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('40000.00'),
            status='Pending'
        )
        # Item 1 belongs to Seller 1
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=1)

        # Seller 1 logs in
        self.client.login(username='seller1_ord', password='SellerPassword123!')
        resp1 = self.client.get(reverse('orders:seller_orders'))
        self.assertEqual(resp1.status_code, 200)
        self.assertTemplateUsed(resp1, 'orders/seller_order_list.html')
        self.assertContains(resp1, f'#{order.purchaseid}')
        self.assertContains(resp1, '1707 Aurangzeb Gold Mohur')

        # Seller 2 logs in (does not own item1)
        self.client.login(username='seller2_ord', password='SellerPassword123!')
        resp2 = self.client.get(reverse('orders:seller_orders'))
        self.assertEqual(resp2.status_code, 200)
        self.assertNotContains(resp2, f'#{order.purchaseid}')

    # -------------------------------------------------------------
    # 6. Admin Master Order Management (DFD 5.1 to 5.3) Tests
    # -------------------------------------------------------------
    def test_admin_master_order_list_and_status_lifecycle(self):
        """
        Admin can view all orders, and progress status through the lifecycle:
        Pending -> Confirmed (DFD 5.1) -> Shipped (DFD 5.2) -> Delivered (DFD 5.3).
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('40000.00'),
            status='Pending',
            pay_status='Unpaid'
        )
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=1)

        self.client.login(username='admin_ord', password='AdminPassword123!')

        # 1. Admin views list
        resp = self.client.get(reverse('orders:admin_orders'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'orders/admin_order_list.html')
        self.assertContains(resp, f'#{order.purchaseid}')
        self.assertContains(resp, 'Pending')

        # 2. DFD 5.1: Confirm Order
        url = reverse('orders:admin_update_status', kwargs={'purchase_id': order.purchaseid})
        self.client.post(url, {'status': 'Confirmed', 'pay_status': 'Paid'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'Confirmed')
        self.assertEqual(order.pay_status, 'Paid')

        # 3. DFD 5.2: Ship Order
        self.client.post(url, {'status': 'Shipped'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'Shipped')

        # 4. DFD 5.3: Deliver Order
        self.client.post(url, {'status': 'Delivered'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'Delivered')

    def test_admin_cancel_order_restocks_items(self):
        """
        Admin cancelling an active order restores item stock.
        """
        # Reduce stock
        Stock.reduce_stock(item_id=self.item1.itemid, quantity=2)
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.cur_stock, 3)

        order = PurchaseMaster.objects.create(
            buyer=self.buyer1,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('80000.00'),
            status='Pending'
        )
        Purchase.objects.create(purchase_master=order, item=self.item1, quantity=2)

        # Admin cancels
        self.client.login(username='admin_ord', password='AdminPassword123!')
        url = reverse('orders:admin_update_status', kwargs={'purchase_id': order.purchaseid})
        self.client.post(url, {'status': 'Cancelled', 'pay_status': 'Refunded'})

        order.refresh_from_db()
        self.assertEqual(order.status, 'Cancelled')
        self.assertEqual(order.pay_status, 'Refunded')

        # Stock restored
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.cur_stock, 5)  # Restored 3 + 2 = 5
