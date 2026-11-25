"""
Test suite for Module 5 – Stock Management & Inventory Control.
Tests:
- Stock model methods & business rules (add_stock, reduce_stock with select_for_update, low-stock threshold 2)
- Automatic status transitions: 'Out of Stock' when cur_stock hits 0, 'Available' when restocked
- Seller "View Stock" (ownership isolation, low stock warnings, search & status filters)
- Seller Restock action (add stock, form validation, 403 on other sellers' items)
- Admin "Stock Management" master table (cross-seller visibility, filters, restock any item)
- Role-based access control (RBAC): Pending sellers and buyers blocked
"""

import io
from PIL import Image
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from decimal import Decimal
from datetime import timedelta
from django.core.exceptions import ValidationError

from accounts.models import Role, UserProfile
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock, InsufficientStockError, Discount
from inventory.forms import DiscountForm
from inventory.utils import get_effective_price
from locations.models import State, District, Location
from orders.models import Cart, PurchaseMaster, Purchase


def create_test_image(filename='antique_stock.jpg', size=(100, 100), color='brown'):
    """Helper to generate a valid test image with Pillow."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')


class Module5StockManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Roles
        cls.admin_role, _ = Role.objects.get_or_create(role='Admin')
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        cls.buyer_role, _ = Role.objects.get_or_create(role='Buyer')

        # 2. Location
        cls.state_kerala = State.objects.create(state='Kerala')
        cls.dist_ernakulam = District.objects.create(dist='Ernakulam', state=cls.state_kerala)
        cls.loc_mattancherry = Location.objects.create(locname='Jew Town, Mattancherry', district=cls.dist_ernakulam)

        # 3. Admin User
        cls.admin_user = User.objects.create_superuser(
            username='admin_stock',
            email='admin@stock.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_stock',
            contactname='Inventory Super Administrator',
            phone='9876543301',
            email='admin@stock.test',
            status='Active'
        )

        # 4. Activated Seller 1
        cls.seller1_user = User.objects.create_user(
            username='seller1_stock',
            email='seller1@stock.test',
            password='SellerPassword123!'
        )
        cls.seller1_profile = UserProfile.objects.create(
            login=cls.seller1_user,
            role=cls.seller_role,
            username='seller1_stock',
            contactname='Cochin Spice & Brass Antiques',
            phone='9876543302',
            email='seller1@stock.test',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_mattancherry,
            status='Active'
        )

        # 5. Activated Seller 2
        cls.seller2_user = User.objects.create_user(
            username='seller2_stock',
            email='seller2@stock.test',
            password='SellerPassword123!'
        )
        cls.seller2_profile = UserProfile.objects.create(
            login=cls.seller2_user,
            role=cls.seller_role,
            username='seller2_stock',
            contactname='Malabar Heritage Dealers',
            phone='9876543303',
            email='seller2@stock.test',
            status='Active'
        )

        # 6. Pending Seller
        cls.pending_seller_user = User.objects.create_user(
            username='pending_seller_stock',
            email='pending@stock.test',
            password='SellerPassword123!'
        )
        cls.pending_seller_profile = UserProfile.objects.create(
            login=cls.pending_seller_user,
            role=cls.seller_role,
            username='pending_seller_stock',
            contactname='Pending Stock Seller',
            phone='9876543304',
            email='pending@stock.test',
            status='Pending'
        )

        # 7. Buyer
        cls.buyer_user = User.objects.create_user(
            username='buyer_stock',
            email='buyer@stock.test',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user,
            role=cls.buyer_role,
            username='buyer_stock',
            contactname='Vintage Collector Buyer',
            phone='9876543305',
            email='buyer@stock.test',
            status='Active'
        )

        # 8. Category & SubCategory
        cls.cat_decor = Category.objects.create(
            category='Decor & Bronzes',
            description='Heritage bronze lamps and vintage wall decor.'
        )
        cls.subcat_lamps = SubCategory.objects.create(
            category=cls.cat_decor,
            subcategory='Kerala Temple Urli & Lamps'
        )

        # 9. Initial Items for Seller 1
        dummy_img = create_test_image('urli.jpg')
        cls.item_seller1 = Item.objects.create(
            item='ANT-URLI-101',
            title='19th Century Bronze Thookku Vilakku Hanging Lamp',
            category=cls.cat_decor,
            subcategory=cls.subcat_lamps,
            years_old=140,
            origin='Kingdom of Travancore',
            price=28000.00,
            status='Available',
            img1=dummy_img,
            description='Cast bronze traditional hanging temple lamp with peacock finial.',
            seller=cls.seller1_user
        )
        cls.stock_seller1 = Stock.objects.create(
            item=cls.item_seller1,
            tot_arr_stock=5,
            cur_stock=5,
            status='In Stock'
        )

        # 10. Initial Item for Seller 2
        cls.item_seller2 = Item.objects.create(
            item='ANT-BRASS-202',
            title='Handcrafted Brass Bell with Garuda Emblem',
            category=cls.cat_decor,
            subcategory=cls.subcat_lamps,
            years_old=110,
            origin='Tanjore, Tamil Nadu',
            price=15000.00,
            status='Available',
            img1=dummy_img,
            description='Ritual temple bell with clear resonance.',
            seller=cls.seller2_user
        )
        cls.stock_seller2 = Stock.objects.create(
            item=cls.item_seller2,
            tot_arr_stock=2,
            cur_stock=2,
            status='In Stock'
        )

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Model Methods & Stock Rules
    # -------------------------------------------------------------
    def test_stock_add_stock_increases_arrived_and_current_and_updates_status(self):
        """
        Stock.add_stock increases both tot_arr_stock and cur_stock, logs stockdate,
        and automatically restores item status to 'Available' if it was 'Out of Stock'.
        """
        # Set item and stock to Out of Stock first
        self.stock_seller1.cur_stock = 0
        self.stock_seller1.save()
        self.item_seller1.refresh_from_db()
        self.assertEqual(self.item_seller1.status, 'Out of Stock')
        self.assertEqual(self.stock_seller1.status, 'Out of Stock')

        old_tot = self.stock_seller1.tot_arr_stock

        # Add 3 units
        self.stock_seller1.add_stock(3)
        self.stock_seller1.refresh_from_db()
        self.item_seller1.refresh_from_db()

        self.assertEqual(self.stock_seller1.tot_arr_stock, old_tot + 3)
        self.assertEqual(self.stock_seller1.cur_stock, 3)
        self.assertEqual(self.stock_seller1.status, 'In Stock')
        self.assertEqual(self.item_seller1.status, 'Available')

    def test_stock_reduce_stock_row_locking_success_and_depletion(self):
        """
        Stock.reduce_stock atomically decrements cur_stock.
        When cur_stock hits 0, marks stock and item 'Out of Stock'.
        """
        # Start with 5 units
        stock = Stock.reduce_stock(self.item_seller1.pk, 3)
        self.assertEqual(stock.cur_stock, 2)
        self.assertEqual(stock.status, 'In Stock')
        self.assertTrue(stock.is_low_stock)  # Threshold 2 is low stock!

        # Reduce remaining 2 units -> hits 0
        stock2 = Stock.reduce_stock(self.item_seller1.pk, 2)
        self.assertEqual(stock2.cur_stock, 0)
        self.assertEqual(stock2.status, 'Out of Stock')
        self.assertTrue(stock2.is_out_of_stock)

        self.item_seller1.refresh_from_db()
        self.assertEqual(self.item_seller1.status, 'Out of Stock')

    def test_stock_reduce_stock_prevents_overselling_with_exception(self):
        """
        Stock.reduce_stock raises InsufficientStockError when requested quantity
        exceeds available stock, preventing overselling.
        """
        # Currently stock has 5 units
        with self.assertRaises(InsufficientStockError) as ctx:
            Stock.reduce_stock(self.item_seller1.pk, 10)

        self.assertIn("Insufficient stock", str(ctx.exception))
        self.stock_seller1.refresh_from_db()
        self.assertEqual(self.stock_seller1.cur_stock, 5)  # Unchanged!

    def test_stock_low_stock_threshold_warnings(self):
        """
        Low-stock threshold warning: 0 < cur_stock <= 2 is low stock.
        cur_stock == 0 is out of stock.
        """
        stock = self.stock_seller1

        # 5 units -> Not low stock, Not out of stock
        stock.cur_stock = 5
        self.assertFalse(stock.is_low_stock)
        self.assertFalse(stock.is_out_of_stock)

        # 2 units -> Low stock
        stock.cur_stock = 2
        self.assertTrue(stock.is_low_stock)
        self.assertFalse(stock.is_out_of_stock)

        # 1 unit -> Low stock
        stock.cur_stock = 1
        self.assertTrue(stock.is_low_stock)
        self.assertFalse(stock.is_out_of_stock)

        # 0 units -> Out of stock, not low stock
        stock.cur_stock = 0
        self.assertFalse(stock.is_low_stock)
        self.assertTrue(stock.is_out_of_stock)

    # -------------------------------------------------------------
    # 2. Seller "View Stock" Dashboard
    # -------------------------------------------------------------
    def test_seller_stock_list_renders_own_items_and_hides_others(self):
        """
        Activated seller views only their own items in the stock ledger.
        """
        self.client.login(username='seller1_stock', password='SellerPassword123!')
        response = self.client.get(reverse('inventory:seller_stock'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/seller_stock_list.html')
        self.assertContains(response, '19th Century Bronze Thookku Vilakku')
        self.assertNotContains(response, 'Handcrafted Brass Bell with Garuda Emblem')
        self.assertContains(response, 'ANT-URLI-101')

    def test_seller_stock_list_filters_by_low_stock(self):
        """
        Seller stock dashboard filters by low_stock status.
        """
        # Set seller1 stock to 2 units (low stock)
        self.stock_seller1.cur_stock = 2
        self.stock_seller1.save()

        self.client.login(username='seller1_stock', password='SellerPassword123!')
        response = self.client.get(f"{reverse('inventory:seller_stock')}?status=low_stock")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ANT-URLI-101')
        self.assertContains(response, 'Low Stock Warning')

    def test_pending_seller_blocked_from_stock_views(self):
        """
        Pending sellers cannot access the stock ledger.
        """
        self.client.login(username='pending_seller_stock', password='SellerPassword123!')
        response = self.client.get(reverse('inventory:seller_stock'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:seller_pending'))

    def test_buyer_blocked_from_seller_stock(self):
        """
        Buyers cannot access seller stock ledger.
        """
        self.client.login(username='buyer_stock', password='BuyerPassword123!')
        response = self.client.get(reverse('inventory:seller_stock'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:role_redirect'), target_status_code=302)

    # -------------------------------------------------------------
    # 3. Seller Restock Actions
    # -------------------------------------------------------------
    def test_seller_can_restock_own_item_successfully(self):
        """
        Seller can restock their own item via the AddStockForm.
        """
        self.client.login(username='seller1_stock', password='SellerPassword123!')

        # GET form
        get_resp = self.client.get(reverse('inventory:seller_add_stock', kwargs={'stock_id': self.stock_seller1.stockid}))
        self.assertEqual(get_resp.status_code, 200)
        self.assertTemplateUsed(get_resp, 'inventory/add_stock_form.html')

        # POST restock 4 units
        post_resp = self.client.post(
            reverse('inventory:seller_add_stock', kwargs={'stock_id': self.stock_seller1.stockid}),
            {'quantity_to_add': 4, 'notes': 'Consignment batch arrival'}
        )
        self.assertEqual(post_resp.status_code, 302)
        self.assertRedirects(post_resp, reverse('inventory:seller_stock'))

        self.stock_seller1.refresh_from_db()
        self.assertEqual(self.stock_seller1.cur_stock, 9)
        self.assertEqual(self.stock_seller1.tot_arr_stock, 9)

    def test_seller_cannot_restock_other_seller_item(self):
        """
        Seller 2 cannot restock Seller 1's item (returns 403 Forbidden).
        """
        self.client.login(username='seller2_stock', password='SellerPassword123!')

        # Attempt GET -> 403
        get_resp = self.client.get(reverse('inventory:seller_add_stock', kwargs={'stock_id': self.stock_seller1.stockid}))
        self.assertEqual(get_resp.status_code, 403)

        # Attempt POST -> 403
        post_resp = self.client.post(
            reverse('inventory:seller_add_stock', kwargs={'stock_id': self.stock_seller1.stockid}),
            {'quantity_to_add': 5}
        )
        self.assertEqual(post_resp.status_code, 403)
        self.stock_seller1.refresh_from_db()
        self.assertEqual(self.stock_seller1.cur_stock, 5)  # Unchanged!

    def test_restock_form_rejects_negative_or_zero_quantity(self):
        """
        Restock form rejects zero and negative quantities.
        """
        self.client.login(username='seller1_stock', password='SellerPassword123!')
        response = self.client.post(
            reverse('inventory:seller_add_stock', kwargs={'stock_id': self.stock_seller1.stockid}),
            {'quantity_to_add': 0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'quantity_to_add', 'Quantity to add must be at least 1 unit.')

    # -------------------------------------------------------------
    # 4. Admin "Stock Management" Master Console
    # -------------------------------------------------------------
    def test_admin_stock_list_shows_all_sellers_and_metrics(self):
        """
        Admin stock console shows all items across all sellers.
        """
        self.client.login(username='admin_stock', password='AdminPassword123!')
        response = self.client.get(reverse('inventory:admin_stock'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/admin_stock_list.html')
        self.assertContains(response, '19th Century Bronze Thookku Vilakku')
        self.assertContains(response, 'Handcrafted Brass Bell with Garuda Emblem')
        self.assertContains(response, 'Cochin Spice &amp; Brass Antiques')
        self.assertContains(response, 'Malabar Heritage Dealers')

    def test_admin_can_restock_any_seller_item(self):
        """
        Admin can restock items belonging to any seller.
        """
        self.client.login(username='admin_stock', password='AdminPassword123!')

        response = self.client.post(
            reverse('inventory:admin_add_stock', kwargs={'stock_id': self.stock_seller2.stockid}),
            {'quantity_to_add': 10}
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:admin_stock'))

        self.stock_seller2.refresh_from_db()
        self.assertEqual(self.stock_seller2.cur_stock, 12)
        self.assertEqual(self.stock_seller2.tot_arr_stock, 12)


# ======================================================================
# Module 12: Promotional Discounts Test Suite
# ======================================================================

class Module12DiscountHelperTests(TestCase):
    """
    Tests for the centralized get_effective_price(item, as_of_date) helper function
    and the Item model delegation properties (has_discount, discounted_price, discount_percent).
    """
    @classmethod
    def setUpTestData(cls):
        cls.state = State.objects.create(state='Tamil Nadu')
        cls.district = District.objects.create(dist='Thanjavur', state=cls.state)
        cls.location = Location.objects.create(locname='Old Thanjavur Heritage Lane', district=cls.district)

        cls.seller_user = User.objects.create_user(
            username='chola_dealer',
            email='chola@test.com',
            password='TestPassword123!'
        )
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        UserProfile.objects.create(
            login=cls.seller_user,
            role=cls.seller_role,
            username='chola_dealer',
            contactname='Chola Antiques',
            phone='9876543210',
            email='chola@test.com',
            state=cls.state,
            district=cls.district,
            location=cls.location,
            status='Active'
        )

        cls.cat_bronze = Category.objects.create(category='Chola Bronzes', description='Ancient South Indian bronze sculptures')
        cls.subcat_bronze = SubCategory.objects.create(category=cls.cat_bronze, subcategory='Deity Idols')

        cls.cat_paintings = Category.objects.create(category='Tanjore Paintings', description='Gold leaf antique paintings')
        cls.subcat_paintings = SubCategory.objects.create(category=cls.cat_paintings, subcategory='Classic Tanjore')

        cls.item_nataraja = Item.objects.create(
            seller=cls.seller_user,
            category=cls.cat_bronze,
            subcategory=cls.subcat_bronze,
            item='CHOLA-NAT-001',
            title='12th Century Bronze Nataraja',
            years_old=800,
            origin='Thanjavur, Tamil Nadu',
            description='Magnificent lost-wax bronze casting with rich patina.',
            img1=create_test_image('nataraja1.jpg'),
            img2=create_test_image('nataraja2.jpg'),
            price=Decimal('10000.00'),
            status='Available'
        )

        cls.item_krishna = Item.objects.create(
            seller=cls.seller_user,
            category=cls.cat_paintings,
            subcategory=cls.subcat_paintings,
            item='TANJ-KRI-002',
            title='Navaneetha Krishna Tanjore Painting',
            years_old=150,
            origin='Thanjavur Palace Guild',
            description='Embossed 22K gold foil with semi-precious Jaipur stones.',
            img1=create_test_image('krishna1.jpg'),
            img2=create_test_image('krishna2.jpg'),
            price=Decimal('5000.00'),
            status='Available'
        )

    def test_get_effective_price_without_discounts(self):
        """When no discounts exist, effective price equals original item price."""
        res = get_effective_price(self.item_nataraja)
        self.assertFalse(res['has_discount'])
        self.assertEqual(res['effective_price'], Decimal('10000.00'))
        self.assertEqual(res['discount_percent'], 0.0)
        self.assertEqual(res['discount_saved'], Decimal('0.00'))
        self.assertIsNone(res['discount'])

        # Check Item model delegation
        self.assertFalse(self.item_nataraja.has_discount)
        self.assertEqual(self.item_nataraja.discounted_price, Decimal('10000.00'))
        self.assertEqual(self.item_nataraja.discount_percent, 0.0)

    def test_get_effective_price_with_active_category_discount(self):
        """Active category discount calculates correct markdown and savings."""
        today = timezone.localdate()
        discount = Discount.objects.create(
            applicable_cat=self.cat_bronze,
            discount_percent=Decimal('20.00'),
            startdate=today - timedelta(days=2),
            enddate=today + timedelta(days=5)
        )

        res = get_effective_price(self.item_nataraja)
        self.assertTrue(res['has_discount'])
        self.assertEqual(res['effective_price'], Decimal('8000.00'))
        self.assertEqual(res['discount_percent'], 20.0)
        self.assertEqual(res['discount_saved'], Decimal('2000.00'))
        self.assertEqual(res['discount'], discount)

        # Delegation on Item model
        self.assertTrue(self.item_nataraja.has_discount)
        self.assertEqual(self.item_nataraja.discounted_price, Decimal('8000.00'))
        self.assertEqual(self.item_nataraja.discount_percent, 20.0)

        # Other category items (paintings) are unaffected
        paint_res = get_effective_price(self.item_krishna)
        self.assertFalse(paint_res['has_discount'])
        self.assertEqual(paint_res['effective_price'], Decimal('5000.00'))

    def test_expired_discount_automatically_stops_applying(self):
        """Past/expired discount does not apply to item pricing."""
        today = timezone.localdate()
        Discount.objects.create(
            applicable_cat=self.cat_bronze,
            discount_percent=Decimal('35.00'),
            startdate=today - timedelta(days=20),
            enddate=today - timedelta(days=1)
        )

        res = get_effective_price(self.item_nataraja)
        self.assertFalse(res['has_discount'])
        self.assertEqual(res['effective_price'], Decimal('10000.00'))
        self.assertEqual(res['discount_percent'], 0.0)
        self.assertFalse(self.item_nataraja.has_discount)
        self.assertEqual(self.item_nataraja.discounted_price, Decimal('10000.00'))

    def test_upcoming_discount_does_not_apply_prematurely(self):
        """Future scheduled discount does not apply before its start date."""
        today = timezone.localdate()
        Discount.objects.create(
            applicable_cat=self.cat_bronze,
            discount_percent=Decimal('50.00'),
            startdate=today + timedelta(days=3),
            enddate=today + timedelta(days=10)
        )

        res = get_effective_price(self.item_nataraja)
        self.assertFalse(res['has_discount'])
        self.assertEqual(res['effective_price'], Decimal('10000.00'))

    def test_storewide_discount_applies_across_all_categories(self):
        """A storewide discount (applicable_cat=None) marks down items in all categories."""
        today = timezone.localdate()
        Discount.objects.create(
            applicable_cat=None,
            discount_percent=Decimal('15.00'),
            startdate=today - timedelta(days=1),
            enddate=today + timedelta(days=10)
        )

        res_nataraja = get_effective_price(self.item_nataraja)
        self.assertTrue(res_nataraja['has_discount'])
        self.assertEqual(res_nataraja['effective_price'], Decimal('8500.00'))
        self.assertEqual(res_nataraja['discount_saved'], Decimal('1500.00'))

        res_krishna = get_effective_price(self.item_krishna)
        self.assertTrue(res_krishna['has_discount'])
        self.assertEqual(res_krishna['effective_price'], Decimal('4250.00'))
        self.assertEqual(res_krishna['discount_saved'], Decimal('750.00'))

    def test_highest_discount_wins_when_multiple_apply(self):
        """When category and storewide discounts both exist, highest percentage wins."""
        today = timezone.localdate()
        # Storewide 10%
        Discount.objects.create(
            applicable_cat=None,
            discount_percent=Decimal('10.00'),
            startdate=today - timedelta(days=1),
            enddate=today + timedelta(days=5)
        )
        # Chola Bronzes 25%
        Discount.objects.create(
            applicable_cat=self.cat_bronze,
            discount_percent=Decimal('25.00'),
            startdate=today - timedelta(days=1),
            enddate=today + timedelta(days=5)
        )

        # Nataraja gets 25% (highest markdown) -> 7,500
        res_nataraja = get_effective_price(self.item_nataraja)
        self.assertEqual(res_nataraja['discount_percent'], 25.0)
        self.assertEqual(res_nataraja['effective_price'], Decimal('7500.00'))

        # Krishna (Paintings) only has storewide 10% -> 4,500
        res_krishna = get_effective_price(self.item_krishna)
        self.assertEqual(res_krishna['discount_percent'], 10.0)
        self.assertEqual(res_krishna['effective_price'], Decimal('4500.00'))


class Module12DiscountValidationAndFormTests(TestCase):
    """
    Tests for Discount model clean() validation and DiscountForm validation rules.
    """
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(category='Ancient Coins', description='Numismatics')

    def test_valid_discount_creation(self):
        """Valid category and storewide discount configurations pass validation."""
        today = timezone.localdate()
        form = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '20.00',
            'startdate': today,
            'enddate': today + timedelta(days=14),
        })
        self.assertTrue(form.is_valid())
        discount = form.save()
        self.assertEqual(discount.discount_percent, Decimal('20.00'))
        self.assertEqual(discount.applicable_cat, self.category)

    def test_valid_storewide_discount_empty_category(self):
        """Leaving applicable_cat blank creates storewide discount."""
        today = timezone.localdate()
        form = DiscountForm(data={
            'applicable_cat': '',
            'discount_percent': '10.00',
            'startdate': today,
            'enddate': today + timedelta(days=7),
        })
        self.assertTrue(form.is_valid())
        discount = form.save()
        self.assertIsNone(discount.applicable_cat)

    def test_enddate_must_be_strictly_after_startdate(self):
        """End date on or before start date fails form and model validation."""
        today = timezone.localdate()

        # 1. End date equals start date
        form_same = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '15.00',
            'startdate': today,
            'enddate': today,
        })
        self.assertFalse(form_same.is_valid())
        self.assertIn('enddate', form_same.errors)
        self.assertIn("End date must be strictly after", form_same.errors['enddate'][0])

        # 2. End date before start date
        form_before = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '15.00',
            'startdate': today,
            'enddate': today - timedelta(days=1),
        })
        self.assertFalse(form_before.is_valid())
        self.assertIn('enddate', form_before.errors)

        # 3. Model clean() validation
        d = Discount(
            applicable_cat=self.category,
            discount_percent=Decimal('15.00'),
            startdate=today,
            enddate=today
        )
        with self.assertRaises(ValidationError):
            d.clean()

    def test_discount_percent_boundary_validation(self):
        """Discount percentage must be strictly between 1% and 90%."""
        today = timezone.localdate()

        # Less than 1% (e.g. 0.5% or 0%)
        form_zero = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '0.00',
            'startdate': today,
            'enddate': today + timedelta(days=5),
        })
        self.assertFalse(form_zero.is_valid())
        self.assertIn('discount_percent', form_zero.errors)

        # Greater than 90% (e.g. 95%)
        form_excess = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '95.00',
            'startdate': today,
            'enddate': today + timedelta(days=5),
        })
        self.assertFalse(form_excess.is_valid())
        self.assertIn('discount_percent', form_excess.errors)

        # Boundary values 1% and 90% are allowed
        form_min = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '1.00',
            'startdate': today,
            'enddate': today + timedelta(days=5),
        })
        self.assertTrue(form_min.is_valid())

        form_max = DiscountForm(data={
            'applicable_cat': self.category.pk,
            'discount_percent': '90.00',
            'startdate': today,
            'enddate': today + timedelta(days=5),
        })
        self.assertTrue(form_max.is_valid())


class Module12AdminDiscountCRUDTests(TestCase):
    """
    Tests for Admin Promotional Discounts CRUD workflows and access control.
    """
    @classmethod
    def setUpTestData(cls):
        # Admin
        cls.admin_role, _ = Role.objects.get_or_create(role='Admin')
        cls.admin_user = User.objects.create_superuser('disc_admin', 'discadmin@test.com', 'AdminPass123!')
        UserProfile.objects.create(
            login=cls.admin_user, role=cls.admin_role, username='disc_admin',
            contactname='Discount Administrator', phone='9998887771', email='discadmin@test.com', status='Active'
        )

        # Buyer
        cls.buyer_role, _ = Role.objects.get_or_create(role='Buyer')
        cls.buyer_user = User.objects.create_user('disc_buyer', 'buyer@test.com', 'BuyerPass123!')
        UserProfile.objects.create(
            login=cls.buyer_user, role=cls.buyer_role, username='disc_buyer',
            contactname='Discount Buyer', phone='9998887772', email='buyer@test.com', status='Active'
        )

        # Seller
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        cls.seller_user = User.objects.create_user('disc_seller', 'seller@test.com', 'SellerPass123!')
        UserProfile.objects.create(
            login=cls.seller_user, role=cls.seller_role, username='disc_seller',
            contactname='Discount Seller', phone='9998887773', email='seller@test.com', status='Active'
        )

        cls.cat_manuscripts = Category.objects.create(category='Palm Leaf Manuscripts', description='Ancient texts')

    def test_rbac_access_restrictions(self):
        """Anonymous, Buyer, and Seller users cannot access Admin Discount management."""
        # 1. Anonymous user redirected to login
        resp = self.client.get(reverse('inventory:admin_discounts'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

        # 2. Buyer blocked/redirected
        self.client.login(username='disc_buyer', password='BuyerPass123!')
        resp_buyer = self.client.get(reverse('inventory:admin_discounts'))
        self.assertIn(resp_buyer.status_code, [302, 403])

        # 3. Seller blocked/redirected
        self.client.login(username='disc_seller', password='SellerPass123!')
        resp_seller = self.client.get(reverse('inventory:admin_discounts'))
        self.assertIn(resp_seller.status_code, [302, 403])

    def test_admin_discount_list_view(self):
        """Admin can view discount management dashboard with metrics."""
        today = timezone.localdate()
        Discount.objects.create(
            applicable_cat=self.cat_manuscripts,
            discount_percent=Decimal('25.00'),
            startdate=today - timedelta(days=2),
            enddate=today + timedelta(days=10)
        )
        self.client.login(username='disc_admin', password='AdminPass123!')
        resp = self.client.get(reverse('inventory:admin_discounts'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'inventory/admin_discount_list.html')
        self.assertContains(resp, 'Palm Leaf Manuscripts')
        self.assertContains(resp, '25% OFF')
        self.assertContains(resp, 'Active')

    def test_admin_discount_create_category_and_storewide(self):
        """Admin can successfully create both category-specific and storewide discounts."""
        self.client.login(username='disc_admin', password='AdminPass123!')
        today = timezone.localdate()

        # 1. Create Category discount
        resp = self.client.post(reverse('inventory:admin_discount_create'), {
            'applicable_cat': self.cat_manuscripts.pk,
            'discount_percent': '30.00',
            'startdate': today,
            'enddate': today + timedelta(days=20),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('inventory:admin_discounts'))
        self.assertTrue(Discount.objects.filter(applicable_cat=self.cat_manuscripts, discount_percent=30.00).exists())

        # 2. Create Storewide discount
        resp_storewide = self.client.post(reverse('inventory:admin_discount_create'), {
            'applicable_cat': '',
            'discount_percent': '12.50',
            'startdate': today,
            'enddate': today + timedelta(days=10),
        })
        self.assertEqual(resp_storewide.status_code, 302)
        self.assertTrue(Discount.objects.filter(applicable_cat__isnull=True, discount_percent=12.50).exists())

    def test_admin_discount_update(self):
        """Admin can modify existing discount percentages and dates."""
        self.client.login(username='disc_admin', password='AdminPass123!')
        today = timezone.localdate()
        discount = Discount.objects.create(
            applicable_cat=self.cat_manuscripts,
            discount_percent=Decimal('15.00'),
            startdate=today,
            enddate=today + timedelta(days=10)
        )

        resp = self.client.post(reverse('inventory:admin_discount_update', kwargs={'discount_id': discount.discountid}), {
            'applicable_cat': self.cat_manuscripts.pk,
            'discount_percent': '45.00',
            'startdate': today,
            'enddate': today + timedelta(days=25),
        })
        self.assertEqual(resp.status_code, 302)
        discount.refresh_from_db()
        self.assertEqual(discount.discount_percent, Decimal('45.00'))
        self.assertEqual(discount.enddate, today + timedelta(days=25))

    def test_admin_discount_delete(self):
        """Admin can delete a discount campaign with confirmation."""
        self.client.login(username='disc_admin', password='AdminPass123!')
        today = timezone.localdate()
        discount = Discount.objects.create(
            applicable_cat=self.cat_manuscripts,
            discount_percent=Decimal('20.00'),
            startdate=today,
            enddate=today + timedelta(days=10)
        )

        # GET confirm page
        resp_get = self.client.get(reverse('inventory:admin_discount_delete', kwargs={'discount_id': discount.discountid}))
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'inventory/admin_discount_confirm_delete.html')

        # POST delete
        resp_post = self.client.post(reverse('inventory:admin_discount_delete', kwargs={'discount_id': discount.discountid}))
        self.assertEqual(resp_post.status_code, 302)
        self.assertFalse(Discount.objects.filter(discountid=discount.discountid).exists())


class Module12BuyerDiscountSearchTests(TestCase):
    """
    Tests for the Buyer "Search item Discount" page (inventory:discount_search).
    """
    @classmethod
    def setUpTestData(cls):
        cls.state = State.objects.create(state='Rajasthan')
        cls.district = District.objects.create(dist='Jaipur', state=cls.state)
        cls.location = Location.objects.create(locname='Johari Bazaar', district=cls.district)

        cls.seller_user = User.objects.create_user('rajasthan_seller', 'raj@test.com', 'Pass123!')
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        UserProfile.objects.create(
            login=cls.seller_user, role=cls.seller_role, username='rajasthan_seller',
            contactname='Jaipur Royal Heritage', phone='9887766554', email='raj@test.com',
            state=cls.state, district=cls.district, location=cls.location, status='Active'
        )

        cls.cat_swords = Category.objects.create(category='Rajput Weaponry', description='Swords and shields')
        cls.subcat_swords = SubCategory.objects.create(category=cls.cat_swords, subcategory='Talwar Swords')

        cls.cat_carpets = Category.objects.create(category='Persian Carpets', description='Handwoven silk rugs')
        cls.subcat_carpets = SubCategory.objects.create(category=cls.cat_carpets, subcategory='Silk Rugs')

        cls.item_talwar = Item.objects.create(
            seller=cls.seller_user, category=cls.cat_swords, subcategory=cls.subcat_swords,
            item='RAJ-TAL-001', title='Damascus Steel Rajput Talwar', years_old=200,
            origin='Jaipur Armoury', description='Gold koftgari decorated hilt with original scabbard.',
            img1=create_test_image('talwar1.jpg'), img2=create_test_image('talwar2.jpg'),
            price=Decimal('15000.00'), status='Available'
        )

        cls.item_carpet = Item.objects.create(
            seller=cls.seller_user, category=cls.cat_carpets, subcategory=cls.subcat_carpets,
            item='PER-CAR-002', title='Isfahan Silk Prayer Rug', years_old=120,
            origin='Persia / Isfahan', description='Pure silk on silk foundation with floral motif.',
            img1=create_test_image('carpet1.jpg'), img2=create_test_image('carpet2.jpg'),
            price=Decimal('25000.00'), status='Available'
        )

    def test_buyer_discount_search_lists_only_active_discounted_items(self):
        """Page shows items that have an active discount and excludes expired or non-discounted items."""
        today = timezone.localdate()

        # Active discount on Rajput Weaponry (20%)
        Discount.objects.create(
            applicable_cat=self.cat_swords,
            discount_percent=Decimal('20.00'),
            startdate=today - timedelta(days=1),
            enddate=today + timedelta(days=10)
        )

        # Expired discount on Persian Carpets (30%)
        Discount.objects.create(
            applicable_cat=self.cat_carpets,
            discount_percent=Decimal('30.00'),
            startdate=today - timedelta(days=20),
            enddate=today - timedelta(days=2)
        )

        resp = self.client.get(reverse('inventory:discount_search'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'inventory/buyer_discount_search.html')

        # Talwar is active -> present
        self.assertContains(resp, 'Damascus Steel Rajput Talwar')
        self.assertContains(resp, '20% OFF')
        self.assertContains(resp, '12000.00')

        # Carpet discount is expired -> NOT listed
        self.assertNotContains(resp, 'Isfahan Silk Prayer Rug')

    def test_buyer_discount_search_filters_and_sorting(self):
        """Keyword search, category filtering, and sorting by discount percentage."""
        today = timezone.localdate()
        # Active discounts on both categories
        Discount.objects.create(
            applicable_cat=self.cat_swords,
            discount_percent=Decimal('15.00'),
            startdate=today,
            enddate=today + timedelta(days=10)
        )
        Discount.objects.create(
            applicable_cat=self.cat_carpets,
            discount_percent=Decimal('40.00'),
            startdate=today,
            enddate=today + timedelta(days=10)
        )

        # 1. Category filter
        resp_cat = self.client.get(reverse('inventory:discount_search'), {'category_id': self.cat_swords.pk})
        self.assertEqual(resp_cat.status_code, 200)
        self.assertContains(resp_cat, 'Damascus Steel Rajput Talwar')
        self.assertNotContains(resp_cat, 'Isfahan Silk Prayer Rug')

        # 2. Keyword query
        resp_q = self.client.get(reverse('inventory:discount_search'), {'q': 'Damascus'})
        self.assertEqual(resp_q.status_code, 200)
        self.assertContains(resp_q, 'Damascus Steel Rajput Talwar')
        self.assertNotContains(resp_q, 'Isfahan Silk Prayer Rug')

        # 3. Sort by highest discount
        resp_sort = self.client.get(reverse('inventory:discount_search'), {'sort': 'discount_desc'})
        self.assertEqual(resp_sort.status_code, 200)
        items = list(resp_sort.context['page_obj'])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0], self.item_carpet)  # 40% > 15%


class Module12OrderPriceSnapshotTests(TestCase):
    """
    Tests for price snapshotting in Purchase table:
    Snapshot the price paid in the Purchase row so later price changes or expired
    discounts do not alter old orders.
    """
    @classmethod
    def setUpTestData(cls):
        cls.state = State.objects.create(state='Karnataka')
        cls.district = District.objects.create(dist='Mysore', state=cls.state)
        cls.location = Location.objects.create(locname='Devaraja Market', district=cls.district)

        # Seller
        cls.seller_user = User.objects.create_user('mysore_seller', 'seller@mysore.test', 'Pass123!')
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        UserProfile.objects.create(
            login=cls.seller_user, role=cls.seller_role, username='mysore_seller',
            contactname='Mysore Heritage Palace Curators', phone='9123456780', email='seller@mysore.test',
            state=cls.state, district=cls.district, location=cls.location, status='Active'
        )

        # Buyer
        cls.buyer_user = User.objects.create_user('royal_collector', 'buyer@mysore.test', 'Pass123!')
        cls.buyer_role, _ = Role.objects.get_or_create(role='Buyer')
        UserProfile.objects.create(
            login=cls.buyer_user, role=cls.buyer_role, username='royal_collector',
            contactname='Royal Antique Collector', phone='9123456781', email='buyer@mysore.test',
            status='Active'
        )

        cls.category = Category.objects.create(category='Sandalwood Carvings', description='Mysore sandalwood artifacts')
        cls.subcategory = SubCategory.objects.create(category=cls.category, subcategory='Inlaid Boxes')

        cls.item = Item.objects.create(
            seller=cls.seller_user, category=cls.category, subcategory=cls.subcategory,
            item='SAN-BOX-001', title='Intricately Carved Mysore Sandalwood Jewellery Box',
            years_old=110, origin='Mysore Royal Court', description='Exquisite micro-carving depicting court scenes.',
            img1=create_test_image('box1.jpg'), img2=create_test_image('box2.jpg'),
            price=Decimal('10000.00'), status='Available'
        )
        Stock.objects.create(item=cls.item, tot_arr_stock=5, cur_stock=5, status='In Stock')

    def test_order_snapshots_discounted_price_and_freezes_against_future_changes(self):
        """
        End-to-End snapshot integrity:
        1. Discount of 20% is active (item price ₹10,000 -> effective ₹8,000).
        2. Buyer purchases 2 units. Purchase row stores price = ₹8,000.
        3. Discount expires, and Seller increases item price to ₹15,000.
        4. Purchase row and order totals still evaluate strictly to ₹8,000 and ₹16,000!
        """
        today = timezone.localdate()
        discount = Discount.objects.create(
            applicable_cat=self.category,
            discount_percent=Decimal('20.00'),
            startdate=today - timedelta(days=2),
            enddate=today + timedelta(days=5)
        )

        # Verify dynamic item discounted price before purchase
        self.assertTrue(self.item.has_discount)
        self.assertEqual(self.item.discounted_price, Decimal('8000.00'))

        # Buyer creates cart item
        cart_item = Cart.objects.create(buyer=self.buyer_user, item=self.item, quantity=2)
        self.assertEqual(cart_item.unit_price, Decimal('8000.00'))
        self.assertEqual(cart_item.subtotal, Decimal('16000.00'))

        # Confirm Order (simulating confirm_order flow)
        order = PurchaseMaster.objects.create(
            buyer=self.buyer_user,
            tot_amt=Decimal('16000.00'),
            pay_status='Unpaid',
            status='Pending'
        )
        purchase = Purchase.objects.create(
            purchase_master=order,
            item=self.item,
            quantity=2,
            price=cart_item.unit_price  # Snapshot price paid!
        )

        self.assertEqual(purchase.price, Decimal('8000.00'))
        self.assertEqual(purchase.unit_price, Decimal('8000.00'))
        self.assertEqual(purchase.subtotal, Decimal('16000.00'))

        # ==============================================================
        # SIMULATE FUTURE DRIFT:
        # A) Discount campaign expires (or is deleted)
        # B) Seller updates item price to ₹18,000.00
        # ==============================================================
        discount.enddate = today - timedelta(days=1)
        discount.save()

        self.item.price = Decimal('18000.00')
        self.item.save()

        # Check current item state (new price, no discount)
        self.assertFalse(self.item.has_discount)
        self.assertEqual(self.item.discounted_price, Decimal('18000.00'))

        # Verify Historical Purchase Integrity
        purchase.refresh_from_db()
        self.assertEqual(purchase.price, Decimal('8000.00'))
        self.assertEqual(purchase.unit_price, Decimal('8000.00'))
        self.assertEqual(purchase.subtotal, Decimal('16000.00'))
        self.assertEqual(order.items_total, Decimal('16000.00'))

    def test_purchase_save_auto_populates_price_if_not_explicitly_set(self):
        """If purchase is saved without explicit price, fallback auto-snapshots current effective price."""
        today = timezone.localdate()
        Discount.objects.create(
            applicable_cat=self.category,
            discount_percent=Decimal('25.00'),
            startdate=today,
            enddate=today + timedelta(days=5)
        )

        order = PurchaseMaster.objects.create(
            buyer=self.buyer_user,
            tot_amt=Decimal('7500.00'),
            pay_status='Unpaid',
            status='Pending'
        )
        # Do not provide price explicitly
        purchase = Purchase.objects.create(
            purchase_master=order,
            item=self.item,
            quantity=1
        )
        purchase.refresh_from_db()
        self.assertEqual(purchase.price, Decimal('7500.00'))  # 10,000 - 25% = 7,500


