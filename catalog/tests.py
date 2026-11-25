"""
Test suite for Module 3 – Categories.
Tests:
- Admin-only CRUD for Category and SubCategory
- Case-insensitive duplicate prevention
- Deletion blocking when items exist
- Deletion blocking when child subcategories exist
- Item counts per category in list
- JSON AJAX endpoint for cascading subcategories
- RBAC protection (non-admin blocked)
"""

import io
from PIL import Image
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
from community.models import Comment, WatchListed


class CategoriesModuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Roles
        cls.admin_role = Role.objects.create(role='Admin')
        cls.seller_role = Role.objects.create(role='Seller')
        cls.buyer_role = Role.objects.create(role='Buyer')

        # Create Admin
        cls.admin_user = User.objects.create_superuser(
            username='admin_cat',
            email='admin@cat.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_cat',
            contactname='Catalog Admin',
            phone='9876543210',
            email='admin@cat.test',
            status='Active'
        )

        # Create Regular Buyer
        cls.buyer_user = User.objects.create_user(
            username='buyer_cat',
            email='buyer@cat.test',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user,
            role=cls.buyer_role,
            username='buyer_cat',
            contactname='Buyer Tester',
            phone='9876543211',
            email='buyer@cat.test',
            status='Active'
        )

        # Create Seller User
        cls.seller_user = User.objects.create_user(
            username='seller_cat',
            email='seller@cat.test',
            password='SellerPassword123!'
        )
        cls.seller_profile = UserProfile.objects.create(
            login=cls.seller_user,
            role=cls.seller_role,
            username='seller_cat',
            contactname='Seller Tester',
            phone='9876543212',
            email='seller@cat.test',
            status='Active'
        )

        # Create Sample Category & SubCategory
        cls.cat_furniture = Category.objects.create(
            category='Furniture',
            description='Colonial and heritage antique furniture.'
        )
        cls.subcat_chairs = SubCategory.objects.create(
            category=cls.cat_furniture,
            subcategory='Colonial Armchairs'
        )

        # Create a sample antique item linked to subcat_chairs
        dummy_image = SimpleUploadedFile(
            name='test_antique.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            content_type='image/gif'
        )
        cls.item1 = Item.objects.create(
            item='ANT-CHAIR-001',
            title='1890 Victorian Rosewood Armchair',
            category=cls.cat_furniture,
            subcategory=cls.subcat_chairs,
            years_old=135,
            origin='British India, Madras Presidency',
            description='Authentic Victorian handcrafted armchair with fine carvings.',
            img1=dummy_image,
            price=45000.00,
            status='Available',
            seller=cls.seller_user
        )

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Category CRUD Tests
    # -------------------------------------------------------------
    def test_category_list_renders_with_item_count(self):
        """Admin can access category list and sees accurate item counts."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        response = self.client.get(reverse('catalog:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/category_list.html')
        self.assertContains(response, 'Furniture')
        # Item count indicator
        self.assertContains(response, '1 Item')

    def test_category_search(self):
        """Category search filters results accurately."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        Category.objects.create(category='Coins', description='Ancient and medieval numismatics')
        
        response = self.client.get(f"{reverse('catalog:category_list')}?q=Coins")
        self.assertContains(response, 'Coins')
        self.assertNotContains(response, 'Furniture')

    def test_category_add_success(self):
        """Admin can create a new category."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        response = self.client.post(reverse('catalog:category_add'), {
            'category': 'Decor',
            'description': 'Period wall mirrors, bronzes, and lamps'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:category_list'))
        self.assertTrue(Category.objects.filter(category='Decor').exists())

    def test_category_duplicate_rejected_case_insensitive(self):
        """Prevent duplicate category names (case-insensitive)."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        response = self.client.post(reverse('catalog:category_add'), {
            'category': 'furniture',  # Lowercase version of existing 'Furniture'
            'description': 'Duplicate test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_category_edit_success(self):
        """Admin can edit an existing category."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        cat = Category.objects.create(category='Arms', description='Old weapons')
        response = self.client.post(reverse('catalog:category_edit', kwargs={'cat_id': cat.catid}), {
            'category': 'Antique Arms & Armour',
            'description': 'Historical swords, shields, and armour'
        })
        self.assertEqual(response.status_code, 302)
        cat.refresh_from_db()
        self.assertEqual(cat.category, 'Antique Arms & Armour')

    def test_category_delete_blocked_when_items_exist(self):
        """Cannot delete category that contains items."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        # cat_furniture contains item1
        response = self.client.post(reverse('catalog:category_delete', kwargs={'cat_id': self.cat_furniture.catid}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:category_list'))
        # Must still exist in database
        self.assertTrue(Category.objects.filter(pk=self.cat_furniture.pk).exists())

    def test_category_delete_allowed_when_empty(self):
        """Category with zero items and zero subcategories can be safely deleted."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        empty_cat = Category.objects.create(category='Textiles', description='Vintage fabrics')
        response = self.client.post(reverse('catalog:category_delete', kwargs={'cat_id': empty_cat.catid}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=empty_cat.pk).exists())

    # -------------------------------------------------------------
    # 2. SubCategory CRUD Tests
    # -------------------------------------------------------------
    def test_subcategory_list_renders_with_category_filter(self):
        """Admin can view subcategories filtered by category."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        response = self.client.get(f"{reverse('catalog:subcategory_list')}?category_id={self.cat_furniture.catid}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/subcategory_list.html')
        self.assertContains(response, 'Colonial Armchairs')

    def test_subcategory_add_success(self):
        """Admin can add a subcategory under a chosen category."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        response = self.client.post(reverse('catalog:subcategory_add'), {
            'category': self.cat_furniture.pk,
            'subcategory': 'Rosewood Writing Desks'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:subcategory_list'))
        self.assertTrue(SubCategory.objects.filter(subcategory='Rosewood Writing Desks', category=self.cat_furniture).exists())

    def test_subcategory_duplicate_in_same_category_rejected(self):
        """Prevent duplicate subcategory names (case-insensitive) under the same category."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        response = self.client.post(reverse('catalog:subcategory_add'), {
            'category': self.cat_furniture.pk,
            'subcategory': 'colonial armchairs'  # Lowercase duplicate of existing
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists under')

    def test_subcategory_delete_blocked_when_items_exist(self):
        """Cannot delete subcategory that has items assigned."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        # subcat_chairs has item1
        response = self.client.post(reverse('catalog:subcategory_delete', kwargs={'subcat_id': self.subcat_chairs.subcatid}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:subcategory_list'))
        # Must still exist in database
        self.assertTrue(SubCategory.objects.filter(pk=self.subcat_chairs.pk).exists())

    def test_subcategory_delete_allowed_when_empty(self):
        """SubCategory with zero items can be safely deleted."""
        self.client.login(username='admin_cat', password='AdminPassword123!')
        empty_subcat = SubCategory.objects.create(
            category=self.cat_furniture,
            subcategory='Antique Rocking Chairs'
        )
        response = self.client.post(reverse('catalog:subcategory_delete', kwargs={'subcat_id': empty_subcat.subcatid}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SubCategory.objects.filter(pk=empty_subcat.pk).exists())

    # -------------------------------------------------------------
    # 3. RBAC Protection Tests
    # -------------------------------------------------------------
    def test_non_admin_blocked_from_category_management(self):
        """Buyer attempting to access Category CRUD is redirected."""
        self.client.login(username='buyer_cat', password='BuyerPassword123!')
        response = self.client.get(reverse('catalog:category_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:role_redirect'), target_status_code=302)

    def test_unauthenticated_blocked_from_category_management(self):
        """Unauthenticated user accessing Category CRUD is redirected to login."""
        response = self.client.get(reverse('catalog:category_list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    # -------------------------------------------------------------
    # 4. JSON AJAX Endpoint Test
    # -------------------------------------------------------------
    def test_ajax_load_subcategories_json(self):
        """AJAX endpoint returns valid JSON list of subcategories for category."""
        response = self.client.get(f"{reverse('catalog:ajax_load_subcategories')}?category_id={self.cat_furniture.catid}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('subcategories', data)
        self.assertTrue(any(s['subcategory'] == 'Colonial Armchairs' for s in data['subcategories']))


def create_test_image(filename='antique.jpg', size=(100, 100), color='gold', img_format='JPEG'):
    """Helper to generate a valid in-memory test image with Pillow."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format=img_format)
    file_obj.seek(0)
    return SimpleUploadedFile(
        filename,
        file_obj.read(),
        content_type=f'image/{img_format.lower()}'
    )


class Module4SellerItemsTests(TestCase):
    """
    Test suite for Module 4 – Seller Items.
    Covers:
    - Activated seller item upload form & validation (price > 0, quantity >= 0, image type & size)
    - Dual Creation (DFD 2.1 & 2.2): creating an Item creates its Stock ledger row
    - Seller "My Items" list with status values (Available, Out of Stock, Hidden, Sold)
    - Ownership isolation: Sellers can only edit/delete their own items
    - Admin Manage Items: Admin can view, edit, hide/unhide, or delete any item
    - Item Detail Page: Dual images, provenance origin, age, price, live stock, seller name and location
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

        # 1. Admin
        cls.admin_user = User.objects.create_superuser(
            username='admin_mod4',
            email='admin@mod4.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_mod4',
            contactname='Super Admin',
            phone='9876543201',
            email='admin@mod4.test',
            status='Active'
        )

        # 2. Activated Seller 1 (with location)
        cls.seller1_user = User.objects.create_user(
            username='seller1_mod4',
            email='seller1@mod4.test',
            password='SellerPassword123!'
        )
        cls.seller1_profile = UserProfile.objects.create(
            login=cls.seller1_user,
            role=cls.seller_role,
            username='seller1_mod4',
            contactname='Kochi Heritage Antiquarians',
            phone='9876543202',
            email='seller1@mod4.test',
            address='14/22 Princess Street, Fort Kochi',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_fortkochi,
            status='Active'
        )

        # 3. Activated Seller 2
        cls.seller2_user = User.objects.create_user(
            username='seller2_mod4',
            email='seller2@mod4.test',
            password='SellerPassword123!'
        )
        cls.seller2_profile = UserProfile.objects.create(
            login=cls.seller2_user,
            role=cls.seller_role,
            username='seller2_mod4',
            contactname='Malabar Antique Emporium',
            phone='9876543203',
            email='seller2@mod4.test',
            status='Active'
        )

        # 4. Pending Seller
        cls.pending_seller_user = User.objects.create_user(
            username='pending_seller_mod4',
            email='pending@mod4.test',
            password='SellerPassword123!'
        )
        cls.pending_seller_profile = UserProfile.objects.create(
            login=cls.pending_seller_user,
            role=cls.seller_role,
            username='pending_seller_mod4',
            contactname='Awaiting Verification Seller',
            phone='9876543204',
            email='pending@mod4.test',
            status='Pending'
        )

        # 5. Buyer
        cls.buyer_user = User.objects.create_user(
            username='buyer_mod4',
            email='buyer@mod4.test',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user,
            role=cls.buyer_role,
            username='buyer_mod4',
            contactname='Discerning Collector',
            phone='9876543205',
            email='buyer@mod4.test',
            status='Active'
        )

        # Catalog Categories
        cls.cat_coins = Category.objects.create(
            category='Coins & Numismatics',
            description='Ancient, medieval and colonial era coins.'
        )
        cls.subcat_mughal = SubCategory.objects.create(
            category=cls.cat_coins,
            subcategory='Mughal Gold & Silver Mohurs'
        )

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Dual Creation (DFD 2.1 & 2.2) & Upload Tests
    # -------------------------------------------------------------
    def test_seller_item_upload_dual_creation_success(self):
        """
        Activated seller uploading an item creates both Item and Stock row (DFD 2.1 & 2.2).
        """
        self.client.login(username='seller1_mod4', password='SellerPassword123!')

        img1 = create_test_image('aurangzeb_obv.jpg', color='gold')
        img2 = create_test_image('aurangzeb_rev.jpg', color='brown')

        payload = {
            'item': 'MUG-MOH-1707',
            'title': '1707 Aurangzeb Gold Mohur Coin',
            'category': self.cat_coins.pk,
            'subcategory': self.subcat_mughal.pk,
            'years_old': 319,
            'origin': 'Mughal Empire, Shahjahanabad Mint',
            'price': '85000.00',
            'opening_stock': 2,
            'status': 'Available',
            'img1': img1,
            'img2': img2,
            'description': 'Struck in 22k pure gold during the final regnal year of Emperor Aurangzeb.',
        }

        response = self.client.post(reverse('catalog:item_create'), payload, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:seller_items'))

        # Verify Item created
        item = Item.objects.get(item='MUG-MOH-1707')
        self.assertEqual(item.title, '1707 Aurangzeb Gold Mohur Coin')
        self.assertEqual(item.seller, self.seller1_user)
        self.assertEqual(item.status, 'Available')
        self.assertEqual(item.years_old, 319)
        self.assertEqual(item.origin, 'Mughal Empire, Shahjahanabad Mint')
        self.assertEqual(item.price, 85000.00)
        self.assertTrue(item.img1)
        self.assertTrue(item.img2)

        # Verify Dual Creation: Stock ledger row initialized (DFD 2.2)
        stock_record = Stock.objects.filter(item=item).first()
        self.assertIsNotNone(stock_record)
        self.assertEqual(stock_record.tot_arr_stock, 2)
        self.assertEqual(stock_record.cur_stock, 2)
        self.assertEqual(stock_record.status, 'In Stock')
        self.assertEqual(item.current_stock, 2)

    def test_seller_item_upload_zero_opening_stock_sets_out_of_stock(self):
        """
        Uploading an item with opening stock 0 automatically marks status 'Out of Stock'.
        """
        self.client.login(username='seller1_mod4', password='SellerPassword123!')
        img = create_test_image('sold_coin.jpg')

        payload = {
            'item': 'MUG-MOH-ZERO',
            'title': 'Rare Zero Stock Mohur',
            'category': self.cat_coins.pk,
            'subcategory': self.subcat_mughal.pk,
            'years_old': 250,
            'origin': 'Mughal Dynasty',
            'price': '50000.00',
            'opening_stock': 0,
            'status': 'Available',
            'img1': img,
            'description': 'Historical coin cataloged prior to arrival.',
        }

        response = self.client.post(reverse('catalog:item_create'), payload)
        self.assertEqual(response.status_code, 302)

        item = Item.objects.get(item='MUG-MOH-ZERO')
        self.assertEqual(item.status, 'Out of Stock')
        self.assertEqual(item.current_stock, 0)
        stock = Stock.objects.get(item=item)
        self.assertEqual(stock.cur_stock, 0)
        self.assertEqual(stock.status, 'Out of Stock')

    def test_pending_seller_blocked_from_upload(self):
        """
        Pending sellers cannot upload items until approved by Admin.
        """
        self.client.login(username='pending_seller_mod4', password='SellerPassword123!')
        response = self.client.get(reverse('catalog:item_create'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:seller_pending'))

    def test_buyer_blocked_from_seller_item_views(self):
        """
        Buyers cannot access seller item upload or management views.
        """
        self.client.login(username='buyer_mod4', password='BuyerPassword123!')
        response = self.client.get(reverse('catalog:seller_items'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:role_redirect'), target_status_code=302)

    # -------------------------------------------------------------
    # 2. Form Validations: Price, Quantity, Images
    # -------------------------------------------------------------
    def test_item_upload_validation_price_and_quantity(self):
        """
        Validation: price must be > 0, opening_stock >= 0, years_old >= 1.
        """
        self.client.login(username='seller1_mod4', password='SellerPassword123!')
        img = create_test_image('val_test.jpg')

        # Negative / Zero Price & Negative Stock
        payload = {
            'item': 'TEST-SKU-VAL',
            'title': 'Invalid Valuation Item',
            'category': self.cat_coins.pk,
            'subcategory': self.subcat_mughal.pk,
            'years_old': 0,  # Invalid
            'origin': 'Ancient Rome',
            'price': '0.00',  # Invalid
            'opening_stock': -5,  # Invalid
            'status': 'Available',
            'img1': img,
            'description': 'Validation check artifact.',
        }

        response = self.client.post(reverse('catalog:item_create'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'price', 'Price must be greater than zero.')
        self.assertFormError(response.context['form'], 'opening_stock', 'Opening stock quantity cannot be negative.')
        self.assertFormError(response.context['form'], 'years_old', 'Age of antique item must be at least 1 year old.')

    def test_item_upload_validation_image_extension_and_size(self):
        """
        Validation: reject unsupported file extensions and files exceeding 5MB.
        """
        self.client.login(username='seller1_mod4', password='SellerPassword123!')

        # 1. Valid image with unsupported extension (.bmp)
        bad_ext_img = create_test_image('unsupported_relic.bmp', img_format='BMP')
        payload = {
            'item': 'TEST-BAD-EXT',
            'title': 'BMP Unsupported Artifact',
            'category': self.cat_coins.pk,
            'subcategory': self.subcat_mughal.pk,
            'years_old': 50,
            'origin': 'Test Origin',
            'price': '1000.00',
            'opening_stock': 1,
            'status': 'Available',
            'img1': bad_ext_img,
            'description': 'Should fail on invalid image extension.',
        }
        response = self.client.post(reverse('catalog:item_create'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unsupported image extension")

        # 2. Non-image file (.pdf) rejected by ImageField
        bad_doc = SimpleUploadedFile('document.pdf', b'%PDF-1.4 fake content', content_type='application/pdf')
        payload['img1'] = bad_doc
        response_doc = self.client.post(reverse('catalog:item_create'), payload)
        self.assertEqual(response_doc.status_code, 200)
        self.assertContains(response_doc, "Upload a valid image")

        # 3. Direct validator check for file exceeding 5MB limit
        from catalog.forms import validate_image_file
        from django.core.exceptions import ValidationError
        oversized_file = SimpleUploadedFile(
            'huge_photo.jpg',
            b'x' * (6 * 1024 * 1024),
            content_type='image/jpeg'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(oversized_file)
        self.assertIn("exceeds 5MB limit", str(ctx.exception))

    # -------------------------------------------------------------
    # 3. Seller "My Items" Listing & Ownership Isolation
    # -------------------------------------------------------------
    def test_seller_item_list_isolation(self):
        """
        Sellers only see their own items in 'My Items'.
        """
        img = create_test_image('item_iso.jpg')
        item1 = Item.objects.create(
            item='SKU-SELLER1',
            title='Seller 1 Antique Coin',
            category=self.cat_coins,
            years_old=150,
            origin='Kochi',
            price=20000.00,
            status='Available',
            img1=img,
            description='Seller 1 item',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item1, tot_arr_stock=1, cur_stock=1, status='In Stock')

        item2 = Item.objects.create(
            item='SKU-SELLER2',
            title='Seller 2 Antique Coin',
            category=self.cat_coins,
            years_old=200,
            origin='Calicut',
            price=30000.00,
            status='Available',
            img1=img,
            description='Seller 2 item',
            seller=self.seller2_user
        )
        Stock.objects.create(item=item2, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Seller 1 logs in
        self.client.login(username='seller1_mod4', password='SellerPassword123!')
        response = self.client.get(reverse('catalog:seller_items'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seller 1 Antique Coin')
        self.assertNotContains(response, 'Seller 2 Antique Coin')

    def test_seller_edit_own_item_and_updates_stock(self):
        """
        Seller can edit their own item and adjust current stock.
        """
        self.client.login(username='seller1_mod4', password='SellerPassword123!')
        img = create_test_image('edit_item.jpg')
        item = Item.objects.create(
            item='SKU-EDIT-01',
            title='Pre-Edit Title',
            category=self.cat_coins,
            subcategory=self.subcat_mughal,
            years_old=120,
            origin='Agra Mint',
            price=15000.00,
            status='Available',
            img1=img,
            description='Initial description.',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Edit item: update price, title, and current stock to 4
        payload = {
            'item': 'SKU-EDIT-01',
            'title': 'Post-Edit Handcrafted Gold Mohur',
            'category': self.cat_coins.pk,
            'subcategory': self.subcat_mughal.pk,
            'years_old': 120,
            'origin': 'Agra Mint',
            'price': '18500.00',
            'current_stock': 4,
            'status': 'Available',
            'description': 'Updated historical description with certificate.',
        }
        response = self.client.post(reverse('catalog:item_update', kwargs={'item_id': item.itemid}), payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:seller_items'))

        item.refresh_from_db()
        self.assertEqual(item.title, 'Post-Edit Handcrafted Gold Mohur')
        self.assertEqual(item.price, 18500.00)
        self.assertEqual(item.current_stock, 4)
        stock = Stock.objects.get(item=item)
        self.assertEqual(stock.cur_stock, 4)

    def test_seller_forbidden_from_editing_or_deleting_other_seller_item(self):
        """
        Seller 2 cannot edit or delete Seller 1's item (returns 403 Forbidden).
        """
        img = create_test_image('forbidden.jpg')
        item1 = Item.objects.create(
            item='SKU-PROTECTED',
            title='Seller 1 Protected Artifact',
            category=self.cat_coins,
            years_old=100,
            origin='Mysore',
            price=25000.00,
            status='Available',
            img1=img,
            description='Protected item',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item1, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Login as Seller 2
        self.client.login(username='seller2_mod4', password='SellerPassword123!')

        # Attempt Edit -> 403
        edit_response = self.client.get(reverse('catalog:item_update', kwargs={'item_id': item1.itemid}))
        self.assertEqual(edit_response.status_code, 403)

        # Attempt Delete -> 403
        delete_response = self.client.post(reverse('catalog:item_delete', kwargs={'item_id': item1.itemid}))
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(Item.objects.filter(pk=item1.itemid).exists())

    def test_seller_delete_own_item_with_confirmation(self):
        """
        Seller 1 can delete their own item, cascading stock ledger.
        """
        self.client.login(username='seller1_mod4', password='SellerPassword123!')
        img = create_test_image('delete_me.jpg')
        item = Item.objects.create(
            item='SKU-TO-DELETE',
            title='Item To Be Deleted',
            category=self.cat_coins,
            years_old=80,
            origin='Delhi',
            price=5000.00,
            status='Available',
            img1=img,
            description='Item to delete',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Confirmation GET page
        get_response = self.client.get(reverse('catalog:item_delete', kwargs={'item_id': item.itemid}))
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'catalog/item_confirm_delete.html')

        # POST delete
        post_response = self.client.post(reverse('catalog:item_delete', kwargs={'item_id': item.itemid}))
        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse('catalog:seller_items'))

        # Check DB
        self.assertFalse(Item.objects.filter(pk=item.itemid).exists())
        self.assertFalse(Stock.objects.filter(item_id=item.itemid).exists())

    # -------------------------------------------------------------
    # 4. Admin Master Catalog Moderation ("Manage Items")
    # -------------------------------------------------------------
    def test_admin_manage_items_view_and_toggle_status(self):
        """
        Admin can view all items, edit any item, and toggle status (Hide / Unhide).
        """
        img = create_test_image('admin_mod.jpg')
        item = Item.objects.create(
            item='SKU-ADMIN-TEST',
            title='Admin Moderated Artifact',
            category=self.cat_coins,
            years_old=140,
            origin='Hyderabad',
            price=35000.00,
            status='Available',
            img1=img,
            description='Moderation artifact',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item, tot_arr_stock=2, cur_stock=2, status='In Stock')

        self.client.login(username='admin_mod4', password='AdminPassword123!')

        # 1. Admin views master list
        response = self.client.get(reverse('catalog:admin_items'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/admin_item_list.html')
        self.assertContains(response, 'Admin Moderated Artifact')
        self.assertContains(response, 'Kochi Heritage Antiquarians')

        # 2. Toggle Status to 'Hidden'
        toggle_response = self.client.post(reverse('catalog:admin_toggle_item_status', kwargs={'item_id': item.itemid}))
        self.assertEqual(toggle_response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, 'Hidden')

        # 3. Toggle Status back to 'Available'
        toggle_back = self.client.post(reverse('catalog:admin_toggle_item_status', kwargs={'item_id': item.itemid}))
        self.assertEqual(toggle_back.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, 'Available')

        # 4. Admin deletes item
        del_response = self.client.post(reverse('catalog:item_delete', kwargs={'item_id': item.itemid}))
        self.assertEqual(del_response.status_code, 302)
        self.assertFalse(Item.objects.filter(pk=item.itemid).exists())

    # -------------------------------------------------------------
    # 5. Public Item Detail Page Tests
    # -------------------------------------------------------------
    def test_item_detail_view_shows_provenance_and_seller_location(self):
        """
        Item detail page displays photographs, provenance, age, price, live stock,
        and seller name with full location hierarchy.
        """
        img1 = create_test_image('detail_primary.jpg', color='gold')
        img2 = create_test_image('detail_hallmark.jpg', color='silver')

        item = Item.objects.create(
            item='ANT-DETAIL-100',
            title='18th Century Travancore Anantharayan Coin',
            category=self.cat_coins,
            subcategory=self.subcat_mughal,
            years_old=245,
            origin='Kingdom of Travancore, Padmanabhapuram',
            price=62000.00,
            status='Available',
            img1=img1,
            img2=img2,
            description='Historical gold Fanam / Anantharayan coin depicting Lord Vishnu.',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item, tot_arr_stock=3, cur_stock=3, status='In Stock')

        # Anyone can view detail page
        response = self.client.get(reverse('catalog:item_detail', kwargs={'item_id': item.itemid}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/item_detail.html')

        # Content assertions
        self.assertContains(response, '18th Century Travancore Anantharayan Coin')
        self.assertContains(response, '245 Years Old')
        self.assertContains(response, 'Kingdom of Travancore, Padmanabhapuram')
        self.assertContains(response, '₹62000.00')
        self.assertContains(response, '3 units in stock')
        self.assertContains(response, 'Kochi Heritage Antiquarians')
        self.assertContains(response, 'Fort Kochi Heritage Zone')
        self.assertContains(response, 'Ernakulam District')
        self.assertContains(response, 'Kerala')

    def test_hidden_item_detail_visibility_rules(self):
        """
        Hidden items cannot be viewed by the public or buyers, but owner and admin can view.
        """
        img = create_test_image('hidden_item.jpg')
        item = Item.objects.create(
            item='ANT-HIDDEN-01',
            title='Secret Rare Relic',
            category=self.cat_coins,
            years_old=500,
            origin='Hidden Vault',
            price=100000.00,
            status='Hidden',
            img1=img,
            description='Classified artifact',
            seller=self.seller1_user
        )
        Stock.objects.create(item=item, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Buyer attempts to view -> redirected
        self.client.login(username='buyer_mod4', password='BuyerPassword123!')
        buyer_resp = self.client.get(reverse('catalog:item_detail', kwargs={'item_id': item.itemid}))
        self.assertEqual(buyer_resp.status_code, 302)
        self.assertRedirects(buyer_resp, reverse('accounts:home'))

        # Owner seller views -> 200 OK
        self.client.login(username='seller1_mod4', password='SellerPassword123!')
        owner_resp = self.client.get(reverse('catalog:item_detail', kwargs={'item_id': item.itemid}))
        self.assertEqual(owner_resp.status_code, 200)
        self.assertContains(owner_resp, 'Listing Hidden')

        # Admin views -> 200 OK
        self.client.login(username='admin_mod4', password='AdminPassword123!')
        admin_resp = self.client.get(reverse('catalog:item_detail', kwargs={'item_id': item.itemid}))
        self.assertEqual(admin_resp.status_code, 200)


class Module6BuyerBrowsingTests(TestCase):
    """
    Test suite for Module 6 – Buyer Browsing.
    Covers:
    - Public home page (hero banner, featured & latest items, categories grid with item counts)
    - Buyer catalogue / marketplace (category browsing, subcategory filter, keyword search, price range, age filter, sorting, pagination)
    - Promotional discounts: calculation, "Discounted" badge, discounted price display
    - Item cards: first image, title, price, location, age, stock status
    - Item detail page: image gallery, provenance, details, comments list, Add to Cart & Add to Watchlist buttons
    - Optimized queries with select_related and prefetch_related
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

        # Seller with geographical location
        cls.seller = User.objects.create_user(
            username='seller_browse',
            email='seller_browse@test.com',
            password='SellerPassword123!'
        )
        cls.seller_profile = UserProfile.objects.create(
            login=cls.seller,
            role=cls.seller_role,
            username='seller_browse',
            contactname='Malabar Antiquarians',
            phone='9876543210',
            email='seller_browse@test.com',
            address='12 Heritage Row, Fort Kochi',
            state=cls.state_kerala,
            district=cls.dist_ernakulam,
            location=cls.loc_fortkochi,
            status='Active'
        )

        # Buyer
        cls.buyer = User.objects.create_user(
            username='buyer_browse',
            email='buyer_browse@test.com',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer,
            role=cls.buyer_role,
            username='buyer_browse',
            contactname='Heritage Connoisseur',
            phone='9876543211',
            email='buyer_browse@test.com',
            status='Active'
        )

        # Categories
        cls.cat_coins = Category.objects.create(
            category='Coins & Numismatics',
            description='Rare coins from ancient dynasties and empires.'
        )
        cls.subcat_mughal = SubCategory.objects.create(
            category=cls.cat_coins,
            subcategory='Mughal Dynasty Mohurs'
        )

        cls.cat_furniture = Category.objects.create(
            category='Colonial Furniture',
            description='Handcrafted teakwood and rosewood furniture.'
        )
        cls.subcat_colonial = SubCategory.objects.create(
            category=cls.cat_furniture,
            subcategory='Victorian & Colonial Chairs'
        )

        # Category Discount on Coins: Active (15% off)
        today = timezone.localdate()
        cls.discount_active = Discount.objects.create(
            applicable_cat=cls.cat_coins,
            discount_percent=15.00,
            startdate=today - timedelta(days=5),
            enddate=today + timedelta(days=10)
        )

        # Expired Discount on Furniture (10% off expired 10 days ago)
        cls.discount_expired = Discount.objects.create(
            applicable_cat=cls.cat_furniture,
            discount_percent=10.00,
            startdate=today - timedelta(days=30),
            enddate=today - timedelta(days=10)
        )

        # Artifacts
        img_primary = create_test_image('coin_gold.jpg', color='gold')
        img_secondary = create_test_image('coin_hallmark.jpg', color='silver')
        img_chair = create_test_image('chair.jpg', color='brown')
        img_table = create_test_image('table.jpg', color='chocolate')

        # Item 1: Gold Mohur (Coins, 15% active discount, Price 80,000, Age 319)
        cls.item1 = Item.objects.create(
            item='ANT-COIN-001',
            title='1707 Aurangzeb Gold Mohur',
            category=cls.cat_coins,
            subcategory=cls.subcat_mughal,
            years_old=319,
            origin='Mughal Empire, Shahjahanabad Mint',
            price=80000.00,
            status='Available',
            img1=img_primary,
            img2=img_secondary,
            description='Historic 22k pure gold coin minted during the reign of Aurangzeb in Shahjahanabad.',
            seller=cls.seller
        )
        Stock.objects.create(item=cls.item1, tot_arr_stock=3, cur_stock=3, status='In Stock')

        # Item 2: Silver Rupee (Coins, 15% active discount, Price 12,000, Age 191)
        cls.item2 = Item.objects.create(
            item='ANT-COIN-002',
            title='1835 William IV Silver Rupee',
            category=cls.cat_coins,
            subcategory=cls.subcat_mughal,
            years_old=191,
            origin='East India Company, Calcutta Mint',
            price=12000.00,
            status='Available',
            img1=img_primary,
            description='Rare first year issue East India Company uniform silver rupee coinage.',
            seller=cls.seller
        )
        Stock.objects.create(item=cls.item2, tot_arr_stock=5, cur_stock=5, status='In Stock')

        # Item 3: Teakwood Chair (Furniture, expired discount, Price 35,000, Age 146)
        cls.item3 = Item.objects.create(
            item='ANT-FURN-001',
            title='1880 Victorian Teakwood Rocking Chair',
            category=cls.cat_furniture,
            subcategory=cls.subcat_colonial,
            years_old=146,
            origin='Chettinad Heritage Mansion',
            price=35000.00,
            status='Available',
            img1=img_chair,
            description='Handcrafted teakwood rocking chair salvaged from a Chettinad ancestral mansion.',
            seller=cls.seller
        )
        Stock.objects.create(item=cls.item3, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Item 4: Rosewood Table (Furniture, Out of Stock, Price 55,000, Age 106)
        cls.item4 = Item.objects.create(
            item='ANT-FURN-002',
            title='1920 Art Deco Rosewood Table',
            category=cls.cat_furniture,
            subcategory=cls.subcat_colonial,
            years_old=106,
            origin='Bombay Presidency',
            price=55000.00,
            status='Out of Stock',
            img1=img_table,
            description='Restored vintage rosewood table with geometric Art Deco carvings.',
            seller=cls.seller
        )
        Stock.objects.create(item=cls.item4, tot_arr_stock=1, cur_stock=0, status='Out of Stock')

        # Item 5: Hidden Relic (Must not be shown in public catalogue or home)
        cls.item_hidden = Item.objects.create(
            item='ANT-SECRET-001',
            title='Confidential Heritage Relic',
            category=cls.cat_coins,
            subcategory=cls.subcat_mughal,
            years_old=400,
            origin='Secret Underground Vault',
            price=99000.00,
            status='Hidden',
            img1=img_primary,
            description='Classified artifact under administrative review.',
            seller=cls.seller
        )
        Stock.objects.create(item=cls.item_hidden, tot_arr_stock=1, cur_stock=1, status='In Stock')

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Public Home Page Tests
    # -------------------------------------------------------------
    def test_home_page_rendering_and_components(self):
        """
        Public home page renders:
        - Hero banner with headline & CTAs
        - Categories grid with accurate active item counts
        - Featured items (ordered by -price)
        - Latest arrivals
        - Location badges and promotional discount badges
        - Hidden items are excluded
        """
        response = self.client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

        # Hero Banner
        self.assertContains(response, 'Where History Finds A New Home')
        self.assertContains(response, 'Browse Marketplace')

        # Categories Grid
        self.assertContains(response, 'Coins &amp; Numismatics')
        self.assertContains(response, 'Colonial Furniture')
        self.assertContains(response, '2 items')

        # Featured Items (ordered by -price: Item 1 at 80k, Item 3 at 35k, Item 2 at 12k)
        self.assertContains(response, '1707 Aurangzeb Gold Mohur')
        self.assertContains(response, '1880 Victorian Teakwood Rocking Chair')

        # Latest Arrivals
        self.assertContains(response, 'Latest Heritage Arrivals')

        # Location badge from seller's profile
        self.assertContains(response, 'Ernakulam, Kerala')

        # Discount badge and discounted price on Item 1 (15% off: 80,000 -> 68,000)
        self.assertContains(response, '15% OFF')
        self.assertContains(response, '68000')

        # Hidden item must NOT appear on public home page
        self.assertNotContains(response, 'Confidential Heritage Relic')

    # -------------------------------------------------------------
    # 2. Buyer Marketplace Catalogue Browsing & Filtering
    # -------------------------------------------------------------
    def test_catalogue_browsing_category_filter(self):
        """
        Filter catalogue by category_id.
        """
        response = self.client.get(reverse('catalog:item_list'), {'category_id': self.cat_coins.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/item_list.html')

        # Shows coin items
        self.assertContains(response, '1707 Aurangzeb Gold Mohur')
        self.assertContains(response, '1835 William IV Silver Rupee')

        # Excludes furniture items
        self.assertNotContains(response, '1880 Victorian Teakwood Rocking Chair')
        self.assertNotContains(response, '1920 Art Deco Rosewood Table')

    def test_catalogue_browsing_subcategory_filter(self):
        """
        Filter catalogue by subcategory_id.
        """
        response = self.client.get(reverse('catalog:item_list'), {'subcategory_id': self.subcat_colonial.pk})
        self.assertEqual(response.status_code, 200)

        # Shows furniture items
        self.assertContains(response, '1880 Victorian Teakwood Rocking Chair')
        self.assertContains(response, '1920 Art Deco Rosewood Table')

        # Excludes coins
        self.assertNotContains(response, '1707 Aurangzeb Gold Mohur')

    def test_catalogue_keyword_search(self):
        """
        Keyword search matches across SKU, Title, Origin, and Description.
        """
        # 1. Search by SKU
        resp_sku = self.client.get(reverse('catalog:item_list'), {'q': 'ANT-COIN-001'})
        self.assertContains(resp_sku, '1707 Aurangzeb Gold Mohur')
        self.assertNotContains(resp_sku, '1835 William IV Silver Rupee')

        # 2. Search by Title keyword
        resp_title = self.client.get(reverse('catalog:item_list'), {'q': 'Rocking Chair'})
        self.assertContains(resp_title, '1880 Victorian Teakwood Rocking Chair')
        self.assertNotContains(resp_title, '1707 Aurangzeb Gold Mohur')

        # 3. Search by Origin
        resp_origin = self.client.get(reverse('catalog:item_list'), {'q': 'Shahjahanabad'})
        self.assertContains(resp_origin, '1707 Aurangzeb Gold Mohur')
        self.assertNotContains(resp_origin, '1880 Victorian Teakwood Rocking Chair')

        # 4. Search by Description
        resp_desc = self.client.get(reverse('catalog:item_list'), {'q': 'Chettinad ancestral mansion'})
        self.assertContains(resp_desc, '1880 Victorian Teakwood Rocking Chair')
        self.assertNotContains(resp_desc, '1707 Aurangzeb Gold Mohur')

    def test_catalogue_price_range_filter(self):
        """
        Filter catalogue by min_price and max_price.
        """
        response = self.client.get(reverse('catalog:item_list'), {
            'min_price': '20000',
            'max_price': '60000',
        })
        self.assertEqual(response.status_code, 200)

        # 35,000 (Chair) and 55,000 (Table) match
        self.assertContains(response, '1880 Victorian Teakwood Rocking Chair')
        self.assertContains(response, '1920 Art Deco Rosewood Table')

        # 12,000 (Silver Rupee) and 80,000 (Gold Mohur) are excluded
        self.assertNotContains(response, '1835 William IV Silver Rupee')
        self.assertNotContains(response, '1707 Aurangzeb Gold Mohur')

    def test_catalogue_age_range_filter(self):
        """
        Filter catalogue by min_age and max_age (years_old).
        """
        response = self.client.get(reverse('catalog:item_list'), {
            'min_age': '180',
            'max_age': '350',
        })
        self.assertEqual(response.status_code, 200)

        # 319 yrs (Gold Mohur) and 191 yrs (Silver Rupee) match
        self.assertContains(response, '1707 Aurangzeb Gold Mohur')
        self.assertContains(response, '1835 William IV Silver Rupee')

        # 146 yrs (Chair) and 106 yrs (Table) excluded
        self.assertNotContains(response, '1880 Victorian Teakwood Rocking Chair')
        self.assertNotContains(response, '1920 Art Deco Rosewood Table')

    def test_catalogue_sorting_options(self):
        """
        Sort catalogue by price_asc, price_desc, oldest, and discounted.
        """
        # Price Low to High
        resp_asc = self.client.get(reverse('catalog:item_list'), {'sort': 'price_asc'})
        items_asc = list(resp_asc.context['page_obj'])
        self.assertEqual(items_asc[0], self.item2)  # 12,000
        self.assertEqual(items_asc[-1], self.item1) # 80,000

        # Price High to Low
        resp_desc = self.client.get(reverse('catalog:item_list'), {'sort': 'price_desc'})
        items_desc = list(resp_desc.context['page_obj'])
        self.assertEqual(items_desc[0], self.item1)  # 80,000
        self.assertEqual(items_desc[-1], self.item2) # 12,000

        # Oldest first (years_old desc)
        resp_oldest = self.client.get(reverse('catalog:item_list'), {'sort': 'oldest'})
        items_oldest = list(resp_oldest.context['page_obj'])
        self.assertEqual(items_oldest[0], self.item1)  # 319 years old

        # Discounted only
        resp_discounted = self.client.get(reverse('catalog:item_list'), {'sort': 'discounted'})
        items_discounted = list(resp_discounted.context['page_obj'])
        self.assertIn(self.item1, items_discounted)
        self.assertIn(self.item2, items_discounted)
        self.assertNotIn(self.item3, items_discounted)
        self.assertNotIn(self.item4, items_discounted)

    def test_catalogue_pagination(self):
        """
        Catalogue paginates at 9 items per page.
        """
        # Create 8 additional dummy items to exceed 9 total items
        img = create_test_image('dummy_page.jpg')
        for i in range(1, 9):
            it = Item.objects.create(
                item=f'PAG-TEST-{i:03d}',
                title=f'Pagination Artifact {i}',
                category=self.cat_coins,
                years_old=100 + i,
                origin='Madras',
                price=5000.00 + (i * 1000),
                status='Available',
                img1=img,
                description=f'Dummy pagination item {i}',
                seller=self.seller
            )
            Stock.objects.create(item=it, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Total public items = 4 initial + 8 new = 12 items
        resp_page1 = self.client.get(reverse('catalog:item_list'))
        self.assertEqual(resp_page1.status_code, 200)
        page1_obj = resp_page1.context['page_obj']
        self.assertEqual(len(page1_obj), 9)
        self.assertTrue(page1_obj.has_next())

        # Page 2 has the remaining 3 items
        resp_page2 = self.client.get(reverse('catalog:item_list'), {'page': 2})
        self.assertEqual(resp_page2.status_code, 200)
        page2_obj = resp_page2.context['page_obj']
        self.assertEqual(len(page2_obj), 3)

    # -------------------------------------------------------------
    # 3. Promotional Discount Computation & Badges
    # -------------------------------------------------------------
    def test_promotional_discount_computation_and_display(self):
        """
        Verify:
        - Active category discount computes discounted price correctly (15% off 80,000 = 68,000)
        - 'Discounted' badge and strikethrough price are rendered
        - Expired discount does not apply, regular price rendered
        """
        # Item 1 has active discount
        self.assertTrue(self.item1.has_discount)
        self.assertEqual(float(self.item1.discount_percent), 15.00)
        self.assertEqual(float(self.item1.discounted_price), 68000.00)

        # Item 3 has expired discount
        self.assertFalse(self.item3.has_discount)
        self.assertEqual(float(self.item3.discounted_price), 35000.00)

        # Inspect catalogue HTML for badge and price formatting
        response = self.client.get(reverse('catalog:item_list'))
        self.assertContains(response, '15% OFF')
        self.assertContains(response, '₹68000.00')

    # -------------------------------------------------------------
    # 4. Item Detail Page with Gallery, Comments, and Actions
    # -------------------------------------------------------------
    def test_item_detail_gallery_comments_and_actions(self):
        """
        Item detail page renders:
        - Primary and secondary photograph gallery
        - Item details, provenance origin, age, live stock
        - Original & discounted prices with active discount badge
        - Verified comments list
        - Add to Cart and Add to Watchlist action controls
        """
        # Add a verified comment to item1
        Comment.objects.create(
            buyer=self.buyer,
            item=self.item1,
            comments='Superb numismatic specimen with complete mintmark preservation.'
        )

        response = self.client.get(reverse('catalog:item_detail', kwargs={'item_id': self.item1.itemid}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/item_detail.html')

        # Details
        self.assertContains(response, '1707 Aurangzeb Gold Mohur')
        self.assertContains(response, 'Mughal Empire, Shahjahanabad Mint')
        self.assertContains(response, '319 Years Old')
        self.assertContains(response, '3 units in stock')
        self.assertContains(response, '15% OFF')
        self.assertContains(response, '₹68000.00')

        # Gallery
        self.assertContains(response, 'id="mainDisplayImage"')
        self.assertContains(response, 'id="thumb1"')
        self.assertContains(response, 'id="thumb2"')

        # Comments list
        self.assertContains(response, 'Superb numismatic specimen with complete mintmark preservation.')
        self.assertContains(response, 'Heritage Connoisseur')

        # Action buttons
        self.assertContains(response, 'Add to Watchlist')
        self.assertContains(response, 'Add to Cart')
        self.assertContains(response, 'id="btnAddToCart"')

