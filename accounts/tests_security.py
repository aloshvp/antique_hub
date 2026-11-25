"""
Security and Access Control Test Suite for Antique Hub (Module 15 - Security Testing).
Covers:
1. Role-Based Access Control (RBAC):
   - Buyer cannot access Admin URLs (Dashboard, User Management, Reports, Discounts, FAQ Admin)
   - Buyer cannot access Seller URLs (Upload item, Seller inventory/stock, Seller orders, Seller ledger)
   - Unauthenticated visitors are redirected to login.
2. Horizontal Privilege Escalation (IDOR Prevention):
   - Seller cannot edit or delete another seller's antique item listings.
   - Buyer cannot view or pay for another buyer's order.
3. CSRF Protection:
   - State-changing POST requests without CSRF tokens are rejected with HTTP 403 Forbidden.
4. SQL Injection Resilience:
   - Malicious SQL payloads in search queries, category filters, and login fields are safely
     handled via Django's parameterized ORM without syntax errors, data leakage, or crashes.
5. Cross-Site Scripting (XSS) Prevention:
   - Injected script tags (<script>, <img> onerror) in comments, item titles, and profile data
     are sanitized/HTML-escaped and never executed raw in responses.
6. Password Hashing & Cryptographic Storage:
   - Passwords are encrypted using Django's PBKDF2 with SHA-256 algorithm and salt.
   - Plaintext passwords are never stored in the database.
"""

import io
from decimal import Decimal
from PIL import Image

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, identify_hasher
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import Role, UserProfile
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock
from locations.models import State, District, Location
from orders.models import PurchaseMaster, Purchase
from community.models import Comment
from community.utils import sanitize_comment_text


def create_security_test_image(filename='sec_test.jpg', size=(60, 60), color='ivory'):
    """Generate in-memory test image."""
    buffer = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(filename, buffer.read(), content_type='image/jpeg')


class Module15SecurityTests(TestCase):
    """
    Comprehensive Security Verification Test Suite.
    """

    @classmethod
    def setUpTestData(cls):
        # 1. Setup Roles
        cls.admin_role = Role.objects.create(role='Admin')
        cls.seller_role = Role.objects.create(role='Seller')
        cls.buyer_role = Role.objects.create(role='Buyer')

        # 2. Setup Geography
        cls.state = State.objects.create(state='Karnataka')
        cls.dist = District.objects.create(state=cls.state, dist='Mysuru')
        cls.loc = Location.objects.create(district=cls.dist, locname='Palace Heritage Zone')

        # 3. Setup Admin User
        cls.admin_user = User.objects.create_superuser(
            username='admin_sec', email='admin@sec.test', password='AdminSecurePassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user, role=cls.admin_role, username='admin_sec',
            contactname='Admin Officer', phone='9876543210', email='admin@sec.test',
            status='Active', state=cls.state, district=cls.dist, location=cls.loc
        )

        # 4. Setup Seller 1
        cls.seller1_user = User.objects.create_user(
            username='seller1_sec', email='seller1@sec.test', password='SellerPassword123!'
        )
        cls.seller1_profile = UserProfile.objects.create(
            login=cls.seller1_user, role=cls.seller_role, username='seller1_sec',
            contactname='Mysuru Antique Guild', phone='9876543211', email='seller1@sec.test',
            status='Active', state=cls.state, district=cls.dist, location=cls.loc
        )

        # 5. Setup Seller 2
        cls.seller2_user = User.objects.create_user(
            username='seller2_sec', email='seller2@sec.test', password='SellerPassword123!'
        )
        cls.seller2_profile = UserProfile.objects.create(
            login=cls.seller2_user, role=cls.seller_role, username='seller2_sec',
            contactname='Bengaluru Relics Co', phone='9876543212', email='seller2@sec.test',
            status='Active', state=cls.state, district=cls.dist, location=cls.loc
        )

        # 6. Setup Buyer 1
        cls.buyer1_user = User.objects.create_user(
            username='buyer1_sec', email='buyer1@sec.test', password='BuyerPassword123!'
        )
        cls.buyer1_profile = UserProfile.objects.create(
            login=cls.buyer1_user, role=cls.buyer_role, username='buyer1_sec',
            contactname='Curator Vikram', phone='9876543213', email='buyer1@sec.test',
            status='Active', state=cls.state, district=cls.dist, location=cls.loc
        )

        # 7. Setup Buyer 2
        cls.buyer2_user = User.objects.create_user(
            username='buyer2_sec', email='buyer2@sec.test', password='BuyerPassword123!'
        )
        cls.buyer2_profile = UserProfile.objects.create(
            login=cls.buyer2_user, role=cls.buyer_role, username='buyer2_sec',
            contactname='Priya Art Collector', phone='9876543214', email='buyer2@sec.test',
            status='Active', state=cls.state, district=cls.dist, location=cls.loc
        )

        # 8. Setup Catalog Items
        cls.category = Category.objects.create(category='Sandalwood Carvings')
        cls.subcategory = SubCategory.objects.create(category=cls.category, subcategory='Temple Idols')

        cls.item_seller1 = Item.objects.create(
            seller=cls.seller1_user,
            item='SANDAL-001',
            title='18th Century Sandalwood Ganesha',
            category=cls.category,
            subcategory=cls.subcategory,
            years_old=240,
            origin='Mysuru Kingdom',
            price=Decimal('85000.00'),
            status='Available',
            img1=create_security_test_image('ganesha.jpg')
        )
        Stock.objects.create(
            item=cls.item_seller1, tot_arr_stock=3, cur_stock=3,
            stockdate=timezone.now(), status='Available'
        )

        cls.item_seller2 = Item.objects.create(
            seller=cls.seller2_user,
            item='SANDAL-002',
            title='19th Century Rosewood Elephant',
            category=cls.category,
            subcategory=cls.subcategory,
            years_old=160,
            origin='Coorg Forest Area',
            price=45000.00,
            status='Available',
            img1=create_security_test_image('elephant.jpg')
        )
        Stock.objects.create(
            item=cls.item_seller2, tot_arr_stock=2, cur_stock=2,
            stockdate=timezone.now(), status='Available'
        )

    def setUp(self):
        self.client = Client()

    # =========================================================================
    # 1. Role-Based Access Control (RBAC) - Buyer URL Isolation
    # =========================================================================

    def test_unauthenticated_visitors_redirected_to_login(self):
        """Unauthenticated visitor trying to access protected views is redirected to login."""
        protected_urls = [
            reverse('dashboard:admin_dashboard'),
            reverse('catalog:item_create'),
            reverse('orders:cart_view'),
            reverse('orders:buyer_orders'),
        ]
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302, f"Failed URL: {url}")
            self.assertIn(reverse('accounts:login'), res.url)

    def test_buyer_cannot_access_admin_urls(self):
        """Buyer attempting to access admin endpoints is rejected and redirected."""
        self.client.login(username='buyer1_sec', password='BuyerPassword123!')
        admin_urls = [
            reverse('dashboard:admin_dashboard'),
            reverse('dashboard:admin_users'),
            reverse('dashboard:admin_reports_hub'),
            reverse('inventory:admin_discounts'),
            reverse('inventory:admin_discount_create'),
            reverse('community:admin_faq_list'),
        ]
        for url in admin_urls:
            res = self.client.get(url)
            # Decorator redirects non-admins (302) to role_redirect
            self.assertEqual(res.status_code, 302, f"Buyer was not blocked from admin URL: {url}")
            self.assertNotEqual(res.url, url)

    def test_buyer_cannot_access_seller_urls(self):
        """Buyer attempting to access seller portals is rejected and redirected."""
        self.client.login(username='buyer1_sec', password='BuyerPassword123!')
        seller_urls = [
            reverse('catalog:item_create'),
            reverse('catalog:seller_items'),
            reverse('inventory:seller_stock'),
            reverse('orders:seller_orders'),
            reverse('payments:seller_payments'),
        ]
        for url in seller_urls:
            res = self.client.get(url)
            # Decorator redirects non-sellers (302)
            self.assertEqual(res.status_code, 302, f"Buyer was not blocked from seller URL: {url}")

    # =========================================================================
    # 2. Horizontal Privilege Escalation (IDOR Prevention)
    # =========================================================================

    def test_seller_cannot_edit_other_sellers_item(self):
        """
        Seller 2 attempts to edit Seller 1's listing.
        System must reject request with HTTP 403 Forbidden.
        """
        self.client.login(username='seller2_sec', password='SellerPassword123!')
        edit_url = reverse('catalog:item_update', kwargs={'item_id': self.item_seller1.itemid})

        # GET request
        get_res = self.client.get(edit_url)
        self.assertEqual(get_res.status_code, 403)

        # POST tampering attempt
        post_res = self.client.post(edit_url, {
            'title': 'Hacked Listing Name',
            'price': '10.00',
        })
        self.assertEqual(post_res.status_code, 403)

        # Verify database record unchanged
        self.item_seller1.refresh_from_db()
        self.assertEqual(self.item_seller1.title, '18th Century Sandalwood Ganesha')
        self.assertEqual(self.item_seller1.price, Decimal('85000.00'))

    def test_seller_cannot_delete_other_sellers_item(self):
        """
        Seller 2 attempts to delete Seller 1's listing.
        System must reject request with HTTP 403 Forbidden.
        """
        self.client.login(username='seller2_sec', password='SellerPassword123!')
        delete_url = reverse('catalog:item_delete', kwargs={'item_id': self.item_seller1.itemid})

        # POST delete attempt
        post_res = self.client.post(delete_url)
        self.assertEqual(post_res.status_code, 403)

        # Verify item still exists in database
        self.assertTrue(Item.objects.filter(itemid=self.item_seller1.itemid).exists())

    def test_buyer_cannot_view_or_pay_other_buyers_order(self):
        """
        Buyer 2 attempts to access Buyer 1's order checkout/payment page.
        Must be redirected or rejected.
        """
        order = PurchaseMaster.objects.create(
            buyer=self.buyer1_user,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('85000.00'),
            status='Pending',
            pay_status='Unpaid'
        )
        Purchase.objects.create(purchase_master=order, item=self.item_seller1, quantity=1, price=Decimal('85000.00'))

        self.client.login(username='buyer2_sec', password='BuyerPassword123!')
        checkout_url = reverse('payments:checkout_payment', kwargs={'order_id': order.purchaseid})

        res = self.client.get(checkout_url)
        # Unauthorized buyer access should redirect with error message
        self.assertEqual(res.status_code, 302)

    # =========================================================================
    # 3. CSRF Protection Enforced
    # =========================================================================

    def test_post_without_csrf_token_is_rejected_with_403(self):
        """
        Using an enforcing client, any state-altering POST without a valid CSRF token
        must result in HTTP 403 Forbidden.
        """
        csrf_client = Client(enforce_csrf_checks=True)
        login_url = reverse('accounts:login')

        # POST without CSRF token
        res = csrf_client.post(login_url, {
            'username': 'buyer1_sec',
            'password': 'BuyerPassword123!'
        })
        self.assertEqual(res.status_code, 403)

    def test_post_with_csrf_token_is_accepted(self):
        """
        POST request carrying a genuine CSRF token from GET is accepted.
        """
        csrf_client = Client(enforce_csrf_checks=True)
        login_url = reverse('accounts:login')

        get_res = csrf_client.get(login_url)
        csrf_token = get_res.cookies['csrftoken'].value

        post_res = csrf_client.post(login_url, {
            'csrfmiddlewaretoken': csrf_token,
            'username': 'buyer1_sec',
            'password': 'BuyerPassword123!'
        })
        # Successful login redirects to role_redirect (302)
        self.assertEqual(post_res.status_code, 302)
        self.assertEqual(post_res.url, reverse('accounts:role_redirect'))

    # =========================================================================
    # 4. SQL Injection Resilience
    # =========================================================================

    def test_sql_injection_attempt_in_search_query(self):
        """
        Passing classic SQL injection payloads into catalog search must be safely
        escaped by the Django ORM without causing a 500 error or syntax failure.
        """
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE catalog_item; --",
            "1' UNION SELECT username, password FROM auth_user --",
            "admin'--",
            "\" OR \"\"=\"",
        ]
        search_url = reverse('catalog:item_list')

        for payload in payloads:
            res = self.client.get(search_url, {'q': payload})
            # Must return clean 200 OK without server error
            self.assertEqual(res.status_code, 200, f"SQL injection payload triggered failure: {payload}")
            # Ensure catalog table was NOT dropped
            self.assertTrue(Item.objects.filter(itemid=self.item_seller1.itemid).exists())

    def test_sql_injection_attempt_in_login_form(self):
        """
        SQL injection in login credentials must fail authentication safely
        without bypassing password verification or crashing.
        """
        malicious_users = [
            "admin' OR '1'='1",
            "' OR 1=1 --",
            "admin'/*",
        ]
        login_url = reverse('accounts:login')

        for bad_user in malicious_users:
            res = self.client.post(login_url, {
                'username': bad_user,
                'password': 'randompassword',
            })
            # Should re-render login page (200) with error message, not authenticate (302)
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, "Invalid username or password")

    def test_sql_injection_attempt_in_category_filter(self):
        """
        SQL injection payload in numeric category_id GET filter is safely handled.
        """
        res = self.client.get(reverse('catalog:item_list'), {'category': "1 OR 1=1"})
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # 5. Cross-Site Scripting (XSS) Prevention & Sanitization
    # =========================================================================

    def test_xss_in_comment_text_is_stripped_and_escaped(self):
        """
        XSS script payloads submitted in comments are stripped of dangerous tags
        by the sanitization utility and rendered safely without executable JavaScript.
        """
        xss_payload = "<script>alert('XSS-EXPLOIT');</script>Authentic piece with great patina."
        clean_text, is_flagged, err = sanitize_comment_text(xss_payload)

        # <script> tag must be removed by strip_tags
        self.assertNotIn('<script>', clean_text)
        self.assertNotIn('</script>', clean_text)
        self.assertIn('Authentic piece with great patina.', clean_text)

    def test_xss_in_item_title_is_html_escaped_in_response(self):
        """
        If an item contains HTML/JavaScript characters in title, Django template
        auto-escaping must escape them as HTML entities (&lt;script&gt;) rather than
        rendering raw executable DOM tags.
        """
        xss_item = Item.objects.create(
            seller=self.seller1_user,
            item='XSS-TEST-ITEM',
            title='<script>alert("XSS")</script> Bronze Bell',
            category=self.category,
            subcategory=self.subcategory,
            years_old=150,
            origin='Kochi',
            price=Decimal('15000.00'),
            status='Available',
            img1=create_security_test_image('bell.jpg')
        )

        detail_url = reverse('catalog:item_detail', kwargs={'item_id': xss_item.itemid})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, 200)

        # Verify raw script is NOT present
        content = res.content.decode('utf-8')
        self.assertNotIn('<script>alert("XSS")</script>', content)
        # Verify escaped entity IS present
        self.assertIn('&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;', content)

    # =========================================================================
    # 6. Password Hashing & Cryptographic Storage
    # =========================================================================

    def test_user_password_is_cryptographically_hashed_with_pbkdf2(self):
        """
        Verify that user passwords are encrypted using PBKDF2 with SHA256,
        contain a random cryptographic salt, and never store plaintext.
        """
        raw_password = 'MySecretAntiquePassword2026!'
        user = User.objects.create_user(
            username='crypto_test_user',
            email='crypto@sec.test',
            password=raw_password
        )

        # 1. Password in database must NOT be the raw password
        self.assertNotEqual(user.password, raw_password)

        # 2. Must start with pbkdf2_sha256 algorithm identifier
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))

        # 3. Must use the PBKDF2PasswordHasher
        hasher = identify_hasher(user.password)
        self.assertEqual(hasher.algorithm, 'pbkdf2_sha256')

        # 4. Check password verification works as expected
        self.assertTrue(check_password(raw_password, user.password))
        self.assertFalse(check_password('WrongPassword123!', user.password))
