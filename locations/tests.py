"""
Test suite for Module 2 – Admin Locations.
Tests:
- Admin-only CRUD for State (DFD 1.1.1)
- Admin-only CRUD for District (DFD 1.1.2)
- Admin-only CRUD for Location (DFD 1.1.3)
- Deletion blocking when child records exist (Critical Relational Integrity)
- Search & Pagination
- RBAC protection (non-admins blocked)
- JSON AJAX cascading endpoints
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from accounts.models import Role, UserProfile
from locations.models import State, District, Location


class LocationsModuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Roles
        cls.admin_role = Role.objects.create(role='Admin')
        cls.buyer_role = Role.objects.create(role='Buyer')

        # Create Admin User
        cls.admin_user = User.objects.create_superuser(
            username='admin_loc',
            email='admin@locations.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin_user,
            role=cls.admin_role,
            username='admin_loc',
            contactname='Admin Tester',
            phone='9876543210',
            email='admin@locations.test',
            address='Admin Office',
            status='Active'
        )

        # Create Regular Buyer User
        cls.buyer_user = User.objects.create_user(
            username='buyer_loc',
            email='buyer@locations.test',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer_user,
            role=cls.buyer_role,
            username='buyer_loc',
            contactname='Buyer Tester',
            phone='9876543211',
            email='buyer@locations.test',
            address='Buyer Lane',
            status='Active'
        )

        # Setup Initial Hierarchy
        cls.state1 = State.objects.create(state='Karnataka')
        cls.dist1 = District.objects.create(state=cls.state1, dist='Bengaluru Urban')
        cls.loc1 = Location.objects.create(district=cls.dist1, locname='Commercial Street Heritage Zone')

        # Link loc1 to buyer profile to test user-linked location deletion blocking
        cls.buyer_profile.state = cls.state1
        cls.buyer_profile.district = cls.dist1
        cls.buyer_profile.location = cls.loc1
        cls.buyer_profile.save()

    def setUp(self):
        self.client = Client()

    # ------------------------------------------------------------------
    # 1. State CRUD Tests (DFD 1.1.1)
    # ------------------------------------------------------------------
    def test_state_list_renders_for_admin(self):
        """Admin can access state list with search and count."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        response = self.client.get(reverse('locations:state_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'locations/state_list.html')
        self.assertContains(response, 'Karnataka')

    def test_state_search(self):
        """State search filters results correctly."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        State.objects.create(state='Gujarat')
        
        response = self.client.get(f"{reverse('locations:state_list')}?q=Guj")
        self.assertContains(response, 'Gujarat')
        self.assertNotContains(response, 'Karnataka')

    def test_state_add_success(self):
        """Admin can add a new State."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        response = self.client.post(reverse('locations:state_add'), {
            'state': 'Punjab'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('locations:state_list'))
        self.assertTrue(State.objects.filter(state='Punjab').exists())

    def test_state_add_duplicate_rejected(self):
        """Duplicate state names are rejected."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        response = self.client.post(reverse('locations:state_add'), {
            'state': 'Karnataka'  # Already exists
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_state_edit_success(self):
        """Admin can edit an existing State."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        st = State.objects.create(state='Orissa')
        response = self.client.post(reverse('locations:state_edit', kwargs={'state_id': st.stateid}), {
            'state': 'Odisha'
        })
        self.assertEqual(response.status_code, 302)
        st.refresh_from_db()
        self.assertEqual(st.state, 'Odisha')

    def test_state_delete_blocked_when_child_districts_exist(self):
        """Cannot delete a State if child districts exist (Relational Protection)."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        # state1 contains dist1
        response = self.client.post(reverse('locations:state_delete', kwargs={'state_id': self.state1.stateid}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('locations:state_list'))
        # State must still exist!
        self.assertTrue(State.objects.filter(pk=self.state1.pk).exists())

    def test_state_delete_allowed_when_no_children(self):
        """State with zero child districts can be safely deleted."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        empty_state = State.objects.create(state='Goa')
        response = self.client.post(reverse('locations:state_delete', kwargs={'state_id': empty_state.stateid}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(State.objects.filter(pk=empty_state.pk).exists())

    # ------------------------------------------------------------------
    # 2. District CRUD Tests (DFD 1.1.2)
    # ------------------------------------------------------------------
    def test_district_add_success(self):
        """Admin can add a new District under a parent State."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        response = self.client.post(reverse('locations:district_add'), {
            'state': self.state1.pk,
            'dist': 'Mysuru'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('locations:district_list'))
        self.assertTrue(District.objects.filter(dist='Mysuru', state=self.state1).exists())

    def test_district_add_duplicate_in_same_state_rejected(self):
        """Duplicate district name within the same state is rejected."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        response = self.client.post(reverse('locations:district_add'), {
            'state': self.state1.pk,
            'dist': 'Bengaluru Urban'  # Already exists under state1
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists in state')

    def test_district_delete_blocked_when_child_locations_exist(self):
        """Cannot delete District if child locations exist."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        # dist1 contains loc1
        response = self.client.post(reverse('locations:district_delete', kwargs={'dist_id': self.dist1.distid}))
        self.assertEqual(response.status_code, 302)
        # District must still exist!
        self.assertTrue(District.objects.filter(pk=self.dist1.pk).exists())

    def test_district_delete_allowed_when_no_children(self):
        """District with zero child locations can be safely deleted."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        empty_dist = District.objects.create(state=self.state1, dist='Mandya')
        response = self.client.post(reverse('locations:district_delete', kwargs={'dist_id': empty_dist.distid}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(District.objects.filter(pk=empty_dist.pk).exists())

    # ------------------------------------------------------------------
    # 3. Location CRUD Tests (DFD 1.1.3)
    # ------------------------------------------------------------------
    def test_location_add_success(self):
        """Admin can add a new Location under a parent District."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        response = self.client.post(reverse('locations:location_add'), {
            'state': self.state1.pk,
            'district': self.dist1.pk,
            'locname': 'Chickpet Antiques Lane'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('locations:location_list'))
        self.assertTrue(Location.objects.filter(locname='Chickpet Antiques Lane', district=self.dist1).exists())

    def test_location_delete_blocked_when_linked_to_users(self):
        """Cannot delete Location if linked to registered user profiles."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        # loc1 is linked to buyer_profile
        response = self.client.post(reverse('locations:location_delete', kwargs={'loc_id': self.loc1.locid}))
        self.assertEqual(response.status_code, 302)
        # Location must still exist!
        self.assertTrue(Location.objects.filter(pk=self.loc1.pk).exists())

    def test_location_delete_allowed_when_no_linked_users(self):
        """Unused location can be safely deleted."""
        self.client.login(username='admin_loc', password='AdminPassword123!')
        unused_loc = Location.objects.create(district=self.dist1, locname='Indiranagar 100ft Rd')
        response = self.client.post(reverse('locations:location_delete', kwargs={'loc_id': unused_loc.locid}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Location.objects.filter(pk=unused_loc.pk).exists())

    # ------------------------------------------------------------------
    # 4. RBAC Protection Tests (Non-Admin Blocked)
    # ------------------------------------------------------------------
    def test_non_admin_blocked_from_location_management(self):
        """Non-admin (Buyer) attempting to access location management is blocked."""
        self.client.login(username='buyer_loc', password='BuyerPassword123!')
        response = self.client.get(reverse('locations:state_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:role_redirect'), target_status_code=302)

    def test_unauthenticated_blocked_from_location_management(self):
        """Unauthenticated user accessing location management is redirected to login."""
        response = self.client.get(reverse('locations:state_list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    # ------------------------------------------------------------------
    # 5. Cascading JSON AJAX Endpoints
    # ------------------------------------------------------------------
    def test_ajax_load_districts_json(self):
        """load-districts endpoint returns JSON list of districts for state."""
        response = self.client.get(f"{reverse('locations:ajax_load_districts')}?state_id={self.state1.pk}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('districts', data)
        self.assertTrue(any(d['dist'] == 'Bengaluru Urban' for d in data['districts']))

    def test_ajax_load_locations_json(self):
        """load-locations endpoint returns JSON list of locations for district."""
        response = self.client.get(f"{reverse('locations:ajax_load_locations')}?district_id={self.dist1.pk}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('locations', data)
        self.assertTrue(any(l['locname'] == 'Commercial Street Heritage Zone' for l in data['locations']))
