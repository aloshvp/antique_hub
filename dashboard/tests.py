"""
Test suite for Module 13 - Admin Dashboard, User Management & Reports Engine.
Covers:
- Admin Dashboard Overview: Access control, 6 primary KPI calculations, Chart.js datasets,
  and complete sidebar navigation links from synopsis structure.
- Pending Sellers Queue: Approve and Activate, Deactivate actions with status transitions.
- Manage Users Console: Search, role & status filtering, Block / Unblock actions,
  inactive account login prevention, and self-blocking prevention guard.
- Reports Hub & Six Standard Reports:
  1. Users Report
  2. Items Report
  3. Orders Report
  4. Sales Report
  5. Payments Report
  6. Stock Report
- Date range filtering across reports.
- CSV export for all 6 reports (RFC-4180 format, UTF-8 BOM, valid MIME type).
- PDF export for all 6 reports (ReportLab rendering, valid %PDF- magic bytes, styled layout).
"""

import io
from decimal import Decimal
from PIL import Image
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import Role, UserProfile
from locations.models import State, District, Location
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock, Discount
from orders.models import PurchaseMaster, Purchase
from payments.models import Payment
from community.models import Comment


def create_test_image(filename='dash_test.jpg', size=(100, 100), color='brown'):
    """Helper to generate in-memory dummy image."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')


class Module13BaseTestCase(TestCase):
    """Common fixture setup for Module 13 test cases."""
    @classmethod
    def setUpTestData(cls):
        # 1. Roles
        cls.admin_role, _ = Role.objects.get_or_create(role='Admin')
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        cls.buyer_role, _ = Role.objects.get_or_create(role='Buyer')

        # 2. Location
        cls.state = State.objects.create(state='Kerala')
        cls.district = District.objects.create(dist='Ernakulam', state=cls.state)
        cls.location = Location.objects.create(locname='Jew Town', district=cls.district)

        # 3. Administrator
        cls.admin_user = User.objects.create_superuser(
            username='admin_dash',
            email='admin@dash.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_dash',
            contactname='Super Administrator',
            phone='9876543001',
            email='admin@dash.test',
            status='Active'
        )

        # 4. Active Seller
        cls.seller_user = User.objects.create_user(
            username='seller_active',
            email='seller_active@dash.test',
            password='SellerPassword123!'
        )
        cls.seller_profile = UserProfile.objects.create(
            login=cls.seller_user,
            role=cls.seller_role,
            username='seller_active',
            contactname='Malabar Antique Emporium',
            phone='9876543002',
            email='seller_active@dash.test',
            state=cls.state,
            district=cls.district,
            location=cls.location,
            status='Active'
        )

        # 5. Pending Seller
        cls.pending_seller_user = User.objects.create_user(
            username='seller_pending',
            email='seller_pending@dash.test',
            password='PendingPassword123!'
        )
        cls.pending_seller_profile = UserProfile.objects.create(
            login=cls.pending_seller_user,
            role=cls.seller_role,
            username='seller_pending',
            contactname='Travancore Relics Co',
            phone='9876543003',
            email='seller_pending@dash.test',
            state=cls.state,
            district=cls.district,
            location=cls.location,
            status='Pending'
        )

        # 6. Active Buyer
        cls.buyer_user = User.objects.create_user(
            username='buyer_active',
            email='buyer@dash.test',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user,
            role=cls.buyer_role,
            username='buyer_active',
            contactname='Heritage Art Collector',
            phone='9876543004',
            email='buyer@dash.test',
            status='Active'
        )

        # 7. Catalog (Category, SubCategory, Items)
        cls.category = Category.objects.create(category='Temple Bronzes', description='Sacred metal artifacts')
        cls.subcategory = SubCategory.objects.create(category=cls.category, subcategory='Idols')

        cls.item = Item.objects.create(
            seller=cls.seller_user,
            category=cls.category,
            subcategory=cls.subcategory,
            item='KL-BRZ-001',
            title='18th Century Bronze Deepalakshmi Lamp',
            years_old=150,
            origin='Travancore Kingdom',
            description='Handcrafted ceremonial bronze lamp.',
            img1=create_test_image('lamp1.jpg'),
            img2=create_test_image('lamp2.jpg'),
            price=Decimal('12000.00'),
            status='Available'
        )
        cls.stock = Stock.objects.create(
            item=cls.item,
            tot_arr_stock=4,
            cur_stock=4,
            status='In Stock'
        )

        # 8. Completed Order & Payment
        cls.order = PurchaseMaster.objects.create(
            buyer=cls.buyer_user,
            ship_charge=Decimal('150.00'),
            tot_amt=Decimal('12150.00'),
            status='Delivered',
            pay_status='Paid'
        )
        cls.purchase = Purchase.objects.create(
            purchase_master=cls.order,
            item=cls.item,
            quantity=1,
            price=Decimal('12000.00')
        )
        cls.payment = Payment.objects.create(
            buyer=cls.buyer_user,
            purchase_master=cls.order,
            amount=Decimal('12150.00'),
            method='Credit Card',
            status='Success',
            card_last4='4242',
            card_type='Visa',
            bank_name='State Bank of India',
            transaction_ref='TXN-TEST-123456'
        )


class Module13AdminDashboardKPITests(Module13BaseTestCase):
    """Tests for the primary Admin Dashboard overview, KPIs, and sidebar navigation."""

    def test_anonymous_and_non_admin_access_restricted(self):
        """Anonymous, Buyer, and Seller users cannot view Admin Dashboard."""
        # Anonymous -> redirected to login
        resp_anon = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(resp_anon.status_code, 302)
        self.assertIn('/login/', resp_anon.url)

        # Buyer -> redirected with warning/error
        self.client.login(username='buyer_active', password='BuyerPassword123!')
        resp_buyer = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertIn(resp_buyer.status_code, [302, 403])

        # Seller -> redirected
        self.client.login(username='seller_active', password='SellerPassword123!')
        resp_seller = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertIn(resp_seller.status_code, [302, 403])

    def test_admin_dashboard_kpis_and_context(self):
        """Admin views dashboard with accurate KPI totals and Chart.js datasets."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        response = self.client.get(reverse('dashboard:admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/admin_dashboard.html')

        # Check KPIs
        self.assertEqual(response.context['total_users'], 4)  # admin, seller_active, seller_pending, buyer_active
        self.assertEqual(response.context['total_sellers'], 2)
        self.assertEqual(response.context['total_buyers'], 1)
        self.assertEqual(response.context['total_items'], 1)
        self.assertEqual(response.context['total_orders'], 1)
        self.assertEqual(response.context['total_revenue'], Decimal('12150.00'))
        self.assertEqual(response.context['pending_sellers_count'], 1)

        # Check Chart.js JSON variables present in context
        self.assertIn('chart_months_json', response.context)
        self.assertIn('chart_revenue_json', response.context)
        self.assertIn('chart_orders_json', response.context)
        self.assertIn('chart_cat_labels_json', response.context)
        self.assertIn('chart_cat_counts_json', response.context)

        # Check rendered HTML contains elements
        self.assertContains(response, 'Administrative Control Center')
        self.assertContains(response, 'Travancore Relics Co')
        self.assertContains(response, 'salesChart')
        self.assertContains(response, 'categoryChart')

    def test_sidebar_contains_all_synopsis_module_links(self):
        """Sidebar navigation must include all menu links from the synopsis module structure."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Synopsis modules:
        # 1. Locations
        self.assertContains(response, reverse('locations:state_list'))
        self.assertContains(response, reverse('locations:district_list'))
        self.assertContains(response, reverse('locations:location_list'))
        # 2. Categories & Items
        self.assertContains(response, reverse('catalog:category_list'))
        self.assertContains(response, reverse('catalog:admin_items'))
        # 3. Stock & Discounts
        self.assertContains(response, reverse('inventory:admin_stock'))
        self.assertContains(response, reverse('inventory:admin_discounts'))
        # 4. Orders & Payments
        self.assertContains(response, reverse('orders:admin_orders'))
        self.assertContains(response, reverse('payments:admin_payments'))
        # 5. Reviews, Watchlist & FAQs
        self.assertContains(response, reverse('community:admin_comments'))
        self.assertContains(response, reverse('community:admin_watchlist'))
        self.assertContains(response, reverse('community:admin_faq_list'))
        # 6. User Management & Reports
        self.assertContains(response, reverse('dashboard:admin_users'))
        self.assertContains(response, reverse('dashboard:admin_reports_hub'))


class Module13PendingSellerActivationTests(Module13BaseTestCase):
    """Tests for activating and deactivating sellers from the dashboard queue."""

    def test_admin_can_activate_pending_seller(self):
        """Admin approves pending seller, updating status to Active."""
        self.client.login(username='admin_dash', password='AdminPassword123!')

        resp = self.client.get(
            reverse('dashboard:admin_seller_activate', kwargs={'user_id': self.pending_seller_profile.userid})
        )
        self.assertEqual(resp.status_code, 302)

        self.pending_seller_profile.refresh_from_db()
        self.assertEqual(self.pending_seller_profile.status, 'Active')
        self.assertTrue(self.pending_seller_profile.login.is_active)

    def test_admin_can_deactivate_seller(self):
        """Admin deactivates seller, revoking selling privileges."""
        self.client.login(username='admin_dash', password='AdminPassword123!')

        resp = self.client.get(
            reverse('dashboard:admin_seller_deactivate', kwargs={'user_id': self.seller_profile.userid})
        )
        self.assertEqual(resp.status_code, 302)

        self.seller_profile.refresh_from_db()
        self.assertEqual(self.seller_profile.status, 'Inactive')


class Module13ManageUsersTests(Module13BaseTestCase):
    """Tests for the Manage Users console, filters, and Block/Unblock toggle."""

    def test_admin_users_list_search_and_filters(self):
        """Admin users list supports search, role filtering, and status filtering."""
        self.client.login(username='admin_dash', password='AdminPassword123!')

        # 1. Base list
        resp = self.client.get(reverse('dashboard:admin_users'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'dashboard/admin_users.html')
        self.assertContains(resp, 'Heritage Art Collector')
        self.assertContains(resp, 'Malabar Antique Emporium')

        # 2. Search filter
        resp_q = self.client.get(reverse('dashboard:admin_users'), {'q': 'Travancore'})
        self.assertEqual(resp_q.status_code, 200)
        self.assertContains(resp_q, 'Travancore Relics Co')
        self.assertNotContains(resp_q, 'Heritage Art Collector')

        # 3. Role filter
        resp_role = self.client.get(reverse('dashboard:admin_users'), {'role': 'Seller'})
        self.assertEqual(resp_role.status_code, 200)
        self.assertContains(resp_role, 'seller_active')
        self.assertContains(resp_role, 'seller_pending')
        self.assertNotContains(resp_role, 'buyer_active')

        # 4. Status filter
        resp_status = self.client.get(reverse('dashboard:admin_users'), {'status': 'Pending'})
        self.assertEqual(resp_status.status_code, 200)
        self.assertContains(resp_status, 'seller_pending')
        self.assertNotContains(resp_status, 'seller_active')

    def test_block_and_unblock_user_workflow(self):
        """Admin blocks active user (suspending login), then unblocks them."""
        self.client.login(username='admin_dash', password='AdminPassword123!')

        # 1. Block buyer_active
        resp_block = self.client.get(
            reverse('dashboard:admin_user_toggle_status', kwargs={'user_id': self.buyer_profile.userid})
        )
        self.assertEqual(resp_block.status_code, 302)

        self.buyer_profile.refresh_from_db()
        self.assertEqual(self.buyer_profile.status, 'Inactive')
        self.assertFalse(self.buyer_profile.login.is_active)

        # 2. Blocked user cannot log in
        self.client.logout()
        login_resp = self.client.post(reverse('accounts:login'), {
            'username': 'buyer_active',
            'password': 'BuyerPassword123!'
        })
        self.assertEqual(login_resp.status_code, 200)
        self.assertContains(login_resp, "suspended or deactivated")

        # 3. Admin unblocks buyer_active
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp_unblock = self.client.get(
            reverse('dashboard:admin_user_toggle_status', kwargs={'user_id': self.buyer_profile.userid})
        )
        self.assertEqual(resp_unblock.status_code, 302)

        self.buyer_profile.refresh_from_db()
        self.assertEqual(self.buyer_profile.status, 'Active')
        self.assertTrue(self.buyer_profile.login.is_active)

    def test_admin_cannot_block_own_account(self):
        """Security guard: Administrator cannot block their own logged-in account."""
        self.client.login(username='admin_dash', password='AdminPassword123!')

        resp = self.client.get(
            reverse('dashboard:admin_user_toggle_status', kwargs={'user_id': self.admin_profile.userid})
        )
        self.assertEqual(resp.status_code, 302)

        self.admin_profile.refresh_from_db()
        self.assertEqual(self.admin_profile.status, 'Active')  # Unchanged!
        self.assertTrue(self.admin_user.is_active)


class Module13ReportsHubAndExportsTests(Module13BaseTestCase):
    """Tests for the 6 reports, date filtering, CSV streaming, and ReportLab PDF exports."""

    def test_reports_hub_view(self):
        """Reports directory hub displays all 6 report cards."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_reports_hub'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'dashboard/admin_reports_hub.html')
        self.assertContains(resp, 'Users &amp; Roles Report')
        self.assertContains(resp, 'Antique Items Report')
        self.assertContains(resp, 'Master Orders Report')
        self.assertContains(resp, 'Sales &amp; Revenue Report')
        self.assertContains(resp, 'Payments Ledger Report')
        self.assertContains(resp, 'Stock &amp; Depletion Report')

    # -------------------------------------------------------------
    # CSV Exports for all 6 reports
    # -------------------------------------------------------------
    def test_csv_export_users_report(self):
        """Users report exports valid RFC-4180 CSV with UTF-8 BOM."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_report_users'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('User ID,Username,Contact Name,Role,Email,Phone,Location,Status,Date Joined', content)
        self.assertIn('admin_dash', content)
        self.assertIn('Malabar Antique Emporium', content)

    def test_csv_export_items_report(self):
        """Items report exports valid CSV."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_report_items'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('Item SKU,Title,Category,SubCategory,Seller,Age (Yrs),Price (INR),Stock,Status,Post Date', content)
        self.assertIn('KL-BRZ-001', content)
        self.assertIn('12000.00', content)

    def test_csv_export_orders_report(self):
        """Orders report exports valid CSV."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_report_orders'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('Order #,Buyer,Order Date,Items Count,Shipping (INR),Total Amount (INR),Fulfillment Status,Payment Status', content)
        self.assertIn(str(self.order.purchaseid), content)
        self.assertIn('12150.00', content)

    def test_csv_export_sales_report(self):
        """Sales report exports valid CSV."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_report_sales'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('Order #,Date,Buyer,Items Summary,Gross Total (INR),Shipping (INR),Net Revenue (INR),Payment Status', content)
        self.assertIn(str(self.order.purchaseid), content)

    def test_csv_export_payments_report(self):
        """Payments report exports valid CSV."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_report_payments'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('Transaction Ref,Order #,Buyer,Method,Bank Name,Card Network,Card Last 4,Amount (INR),Status,Date', content)
        self.assertIn('TXN-TEST-123456', content)
        self.assertIn('State Bank of India', content)

    def test_csv_export_stock_report(self):
        """Stock report exports valid CSV."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        resp = self.client.get(reverse('dashboard:admin_report_stock'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('Stock ID,Item SKU,Title,Category,Seller,Total Arrived,Current Available,Status,Low Stock Alert,Last Restocked', content)
        self.assertIn('KL-BRZ-001', content)

    # -------------------------------------------------------------
    # PDF Exports for all 6 reports (ReportLab)
    # -------------------------------------------------------------
    def test_pdf_export_all_six_reports(self):
        """All 6 reports export valid publication-quality PDF documents."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        endpoints = [
            'dashboard:admin_report_users',
            'dashboard:admin_report_items',
            'dashboard:admin_report_orders',
            'dashboard:admin_report_sales',
            'dashboard:admin_report_payments',
            'dashboard:admin_report_stock',
        ]
        for ep in endpoints:
            with self.subTest(endpoint=ep):
                resp = self.client.get(reverse(ep), {'export': 'pdf'})
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp['Content-Type'], 'application/pdf')
                # Verify PDF magic header
                self.assertTrue(resp.content.startswith(b'%PDF-'))
                self.assertGreater(len(resp.content), 500)

    # -------------------------------------------------------------
    # Date Filtering Test
    # -------------------------------------------------------------
    def test_date_range_filtering_on_reports(self):
        """Date range filters records strictly within the chosen window."""
        self.client.login(username='admin_dash', password='AdminPassword123!')
        today = timezone.localdate()

        # Query matching today
        resp_match = self.client.get(reverse('dashboard:admin_report_orders'), {
            'start_date': str(today - timedelta(days=1)),
            'end_date': str(today + timedelta(days=1)),
        })
        self.assertEqual(resp_match.status_code, 200)
        self.assertContains(resp_match, str(self.order.purchaseid))

        # Query in past year (excluding today)
        resp_nomatch = self.client.get(reverse('dashboard:admin_report_orders'), {
            'start_date': '2020-01-01',
            'end_date': '2020-12-31',
        })
        self.assertEqual(resp_nomatch.status_code, 200)
        self.assertContains(resp_nomatch, "No Audit Records Found")
