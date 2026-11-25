"""
Comprehensive Test Suite for Module 1 – Accounts.
Tests:
- Unified common login & role-based redirect
- Buyer registration (status Active immediately)
- Seller registration (status Pending awaiting activation)
- Duplicate username & email check (DFD step "Check Existing")
- Indian 10-digit phone regex validation
- Password strength & mismatch validation
- Blocked access / RBAC protection via role_required decorator
- Cascading AJAX endpoints (load districts & locations)
- Real-time DFD check-existing AJAX endpoint
- Admin seller activation workflow (DFD step "Activate Seller")
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from accounts.models import Role, UserProfile
from locations.models import State, District, Location


class AccountsModuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Roles
        cls.admin_role = Role.objects.create(role='Admin')
        cls.seller_role = Role.objects.create(role='Seller')
        cls.buyer_role = Role.objects.create(role='Buyer')

        # Sample Location Hierarchy
        cls.state = State.objects.create(state='Kerala')
        cls.district = District.objects.create(state=cls.state, dist='Ernakulam')
        cls.location = Location.objects.create(district=cls.district, locname='Fort Kochi')

        # Create Admin Superuser
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@antiquehub.com',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin',
            contactname='System Admin',
            phone='9876543210',
            email='admin@antiquehub.com',
            address='Admin HQ',
            state=cls.state,
            district=cls.district,
            location=cls.location,
            status='Active'
        )

        # Create Active Buyer
        cls.buyer_user = User.objects.create_user(
            username='buyer_john',
            email='john@buyer.com',
            password='Password123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user,
            role=cls.buyer_role,
            username='buyer_john',
            contactname='John Collector',
            phone='9876543211',
            email='john@buyer.com',
            address='12 Heritage Lane',
            state=cls.state,
            district=cls.district,
            location=cls.location,
            status='Active'
        )

        # Create Pending Seller
        cls.pending_seller_user = User.objects.create_user(
            username='seller_pending',
            email='pending@seller.com',
            password='Password123!'
        )
        cls.pending_seller_profile = UserProfile.objects.create(
            login=cls.pending_seller_user,
            role=cls.seller_role,
            username='seller_pending',
            contactname='Pending Dealer',
            phone='9876543212',
            email='pending@seller.com',
            address='88 Antique Street',
            state=cls.state,
            district=cls.district,
            location=cls.location,
            status='Pending'
        )

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Login & Role-Based Redirection Tests
    # -------------------------------------------------------------
    def test_buyer_login_and_redirect(self):
        """Buyer login redirects successfully via role_redirect."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'buyer_john',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:role_redirect'))

        # Follow to role_redirect
        follow_response = self.client.get(reverse('accounts:role_redirect'))
        self.assertEqual(follow_response.status_code, 302)

    def test_pending_seller_login_redirects_to_pending_notice(self):
        """Pending seller login routes to seller_pending status notice."""
        self.client.login(username='seller_pending', password='Password123!')
        response = self.client.get(reverse('accounts:role_redirect'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:seller_pending'))

        # Check pending page content
        page_response = self.client.get(reverse('accounts:seller_pending'))
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, 'Your Seller Application is Under Review')

    def test_admin_login_redirects_to_admin_console(self):
        """Administrator login routes to admin dashboard or /admin/."""
        self.client.login(username='admin', password='AdminPassword123!')
        response = self.client.get(reverse('accounts:role_redirect'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/admin/' in response.url or 'dashboard' in response.url)

    # -------------------------------------------------------------
    # 2. Registration & DFD 'Check Existing' Duplicate Validation
    # -------------------------------------------------------------
    def test_buyer_registration_active_immediately(self):
        """Buyer registration succeeds and creates an Active profile immediately."""
        response = self.client.post(reverse('accounts:buyer_register'), {
            'contactname': 'Vikram Mehra',
            'username': 'vikram_m',
            'email': 'vikram@example.com',
            'phone': '9845012345',
            'address': '45 Fort Road',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(response.status_code, 302)

        # Check User & Profile created
        user = User.objects.get(username='vikram_m')
        self.assertEqual(user.email, 'vikram@example.com')
        self.assertEqual(user.userprofile.status, 'Active')
        self.assertEqual(user.userprofile.role.role, 'Buyer')

    def test_seller_registration_starts_pending(self):
        """Seller registration succeeds and creates account with status 'Pending'."""
        response = self.client.post(reverse('accounts:seller_register'), {
            'contactname': 'Royal Antiquities',
            'username': 'royal_antiques',
            'email': 'royal@antiques.com',
            'phone': '9820054321',
            'business_license': 'GSTIN-29AAACB1234',
            'address': '7 Palace Bazaar',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(response.status_code, 302)

        # Check User & Profile created with Pending status
        user = User.objects.get(username='royal_antiques')
        self.assertEqual(user.userprofile.status, 'Pending')
        self.assertEqual(user.userprofile.role.role, 'Seller')

    def test_duplicate_username_rejected(self):
        """DFD Step 'Check Existing': Attempting to register existing username is rejected."""
        response = self.client.post(reverse('accounts:buyer_register'), {
            'contactname': 'Impostor John',
            'username': 'buyer_john',  # Already exists
            'email': 'different_email@example.com',
            'phone': '9845012399',
            'address': '101 Street',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This username is already taken')

    def test_duplicate_email_rejected(self):
        """DFD Step 'Check Existing': Attempting to register existing email is rejected."""
        response = self.client.post(reverse('accounts:buyer_register'), {
            'contactname': 'Duplicate Email User',
            'username': 'new_unique_user',
            'email': 'john@buyer.com',  # Already exists
            'phone': '9845012399',
            'address': '101 Street',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email address is already registered')

    def test_invalid_indian_phone_rejected(self):
        """Phone numbers that do not match 10-digit Indian pattern (6-9) are rejected."""
        response = self.client.post(reverse('accounts:buyer_register'), {
            'contactname': 'Invalid Phone User',
            'username': 'test_phone_user',
            'email': 'phone@example.com',
            'phone': '1234567890',  # Invalid starting digit (must start with 6-9)
            'address': '101 Street',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a valid 10-digit Indian phone number')

    def test_password_strength_and_mismatch(self):
        """Passwords with less than 8 chars or mismatched confirmation are rejected."""
        # Short password
        res1 = self.client.post(reverse('accounts:buyer_register'), {
            'contactname': 'Weak Pwd User',
            'username': 'weak_user',
            'email': 'weak@example.com',
            'phone': '9845012345',
            'address': 'Street',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'abc',
            'confirm_password': 'abc',
        })
        self.assertContains(res1, 'Password must be at least 8 characters long')

        # Mismatched passwords
        res2 = self.client.post(reverse('accounts:buyer_register'), {
            'contactname': 'Mismatch User',
            'username': 'mismatch_user',
            'email': 'mismatch@example.com',
            'phone': '9845012345',
            'address': 'Street',
            'state': self.state.pk,
            'district': self.district.pk,
            'location': self.location.pk,
            'password': 'StrongPassword123!',
            'confirm_password': 'DifferentPassword999!',
        })
        self.assertContains(res2, 'Passwords do not match')

    # -------------------------------------------------------------
    # 3. Blocked Access & RBAC Protection Tests
    # -------------------------------------------------------------
    def test_buyer_blocked_from_admin_seller_list(self):
        """Non-admin (Buyer) attempting to access admin seller console is blocked."""
        self.client.login(username='buyer_john', password='Password123!')
        response = self.client.get(reverse('accounts:admin_seller_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:role_redirect'), target_status_code=302)

    def test_unauthenticated_user_blocked_from_profile(self):
        """Unauthenticated user accessing profile is redirected to login."""
        response = self.client.get(reverse('accounts:profile_view'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    # -------------------------------------------------------------
    # 4. AJAX Endpoints (Cascading & DFD Check Existing)
    # -------------------------------------------------------------
    def test_ajax_load_districts_and_locations(self):
        """Verifies cascading AJAX endpoints return JSON data."""
        res_dist = self.client.get(f"{reverse('locations:ajax_load_districts')}?state_id={self.state.pk}")
        self.assertEqual(res_dist.status_code, 200)
        data_dist = res_dist.json()
        self.assertIn('districts', data_dist)
        self.assertTrue(len(data_dist['districts']) > 0)

        res_loc = self.client.get(f"{reverse('locations:ajax_load_locations')}?district_id={self.district.pk}")
        self.assertEqual(res_loc.status_code, 200)
        data_loc = res_loc.json()
        self.assertIn('locations', data_loc)
        self.assertTrue(len(data_loc['locations']) > 0)

    def test_ajax_check_existing_endpoint(self):
        """DFD AJAX: Real-time endpoint accurately detects existing and available usernames/emails."""
        res1 = self.client.get(f"{reverse('accounts:ajax_check_existing')}?field=username&value=buyer_john")
        self.assertTrue(res1.json()['exists'])

        res2 = self.client.get(f"{reverse('accounts:ajax_check_existing')}?field=username&value=brand_new_collector")
        self.assertFalse(res2.json()['exists'])

        res3 = self.client.get(f"{reverse('accounts:ajax_check_existing')}?field=email&value=john@buyer.com")
        self.assertTrue(res3.json()['exists'])

    # -------------------------------------------------------------
    # 5. Admin Seller Activation Workflow (DFD 'Activate Seller')
    # -------------------------------------------------------------
    def test_admin_can_activate_pending_seller(self):
        """Administrator activates a pending seller, changing status from Pending to Active."""
        self.client.login(username='admin', password='AdminPassword123!')

        self.assertEqual(self.pending_seller_profile.status, 'Pending')

        response = self.client.post(
            reverse('accounts:admin_activate_seller', kwargs={'user_id': self.pending_seller_profile.userid})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:admin_seller_list'))

        self.pending_seller_profile.refresh_from_db()
        self.assertEqual(self.pending_seller_profile.status, 'Active')


class Module14UITests(TestCase):
    """
    Test Suite for Module 14 – UI:
    - Consistent antique-themed layout with navbar (role-aware), footer, breadcrumbs, loading bar
    - Custom error handlers (404, 403, 500)
    - Empty-state illustrations
    - Form validation assets & Image preview components
    """

    @classmethod
    def setUpTestData(cls):
        cls.buyer_role = Role.objects.create(role='Buyer')
        cls.seller_role = Role.objects.create(role='Seller')
        cls.admin_role = Role.objects.create(role='Admin')

        cls.user = User.objects.create_user(username='test_buyer_ui', email='buyer_ui@test.com', password='Password123!')
        cls.profile = UserProfile.objects.create(
            login=cls.user,
            role=cls.buyer_role,
            username='test_buyer_ui',
            contactname='Test Buyer UI',
            phone='9998887776',
            email='buyer_ui@test.com',
            status='Active'
        )

    def test_custom_404_view(self):
        """Custom 404 handler returns status 404 and renders 404.html with antique styling."""
        from antique_hub.views import error_404
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/non-existent-artifact-page/')
        response = error_404(request)
        self.assertEqual(response.status_code, 404)
        content = response.content.decode('utf-8')
        self.assertIn('Artifact Not Found', content)
        self.assertIn('HTTP 404', content)
        self.assertIn('card-antique-dark', content)

    def test_custom_403_view(self):
        """Custom 403 handler returns status 403 and renders 403.html with access denied notice."""
        from antique_hub.views import error_403
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/restricted-admin-vault/')
        response = error_403(request)
        self.assertEqual(response.status_code, 403)
        content = response.content.decode('utf-8')
        self.assertIn('Access Denied', content)
        self.assertIn('HTTP 403', content)
        self.assertIn('card-antique-dark', content)

    def test_custom_500_view(self):
        """Custom 500 handler returns status 500 and renders 500.html with under restoration notice."""
        from antique_hub.views import error_500
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/unexpected-server-error/')
        response = error_500(request)
        self.assertEqual(response.status_code, 500)
        content = response.content.decode('utf-8')
        self.assertIn('Under Restoration', content)
        self.assertIn('HTTP 500', content)
        self.assertIn('card-antique-dark', content)

    def test_base_layout_features(self):
        """Base layout renders role-aware navbar, announcements, footer, and loading progress bar."""
        response = self.client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'globalLoadingBar')
        self.assertContains(response, 'antique-theme.css')
        self.assertContains(response, 'main.js')
        self.assertContains(response, 'ANTIQUE HUB')
        self.assertContains(response, 'mainFooter')

    def test_role_aware_navigation_buyer(self):
        """Navbar displays role-specific links for authenticated buyer."""
        self.client.login(username='test_buyer_ui', password='Password123!')
        response = self.client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'buyerWatchlist')
        self.assertContains(response, 'buyerCart')
        self.assertContains(response, 'buyerOrders')

    def test_empty_state_illustrations_rendered(self):
        """Empty shopping cart renders empty-state-antique illustration."""
        self.client.login(username='test_buyer_ui', password='Password123!')
        response = self.client.get(reverse('orders:cart_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'empty-state-antique')
        self.assertContains(response, 'empty-state-title')
        self.assertContains(response, 'Your Heritage Cart is Currently Empty')

    def test_static_theme_assets_integrity(self):
        """Verify CSS contains spinner, empty-state, preview, and breadcrumb styles."""
        import os
        from django.conf import settings
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'antique-theme.css')
        js_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'main.js')

        self.assertTrue(os.path.exists(css_path))
        self.assertTrue(os.path.exists(js_path))

        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            self.assertIn('globalLoadingBar', css_content)
            self.assertIn('spinner-border-antique', css_content)
            self.assertIn('empty-state-antique', css_content)
            self.assertIn('image-preview-box', css_content)
            self.assertIn('breadcrumb-antique', css_content)

        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            self.assertIn('LoadingBar', js_content)
            self.assertIn('initImagePreviews', js_content)
            self.assertIn('initClientValidation', js_content)
            self.assertIn('validateLuhn', js_content)

