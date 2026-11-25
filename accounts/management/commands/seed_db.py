"""
Management command to seed initial master data for Antique Hub.
Seeds:
- 3 User Roles (Admin, Seller, Buyer)
- 1 Superuser Administrator with attached UserProfile
- 3 States with corresponding Districts and Locations
- 6 Antique Categories with relevant SubCategories
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from accounts.models import Role, UserProfile
from locations.models import State, District, Location
from catalog.models import Category, SubCategory


class Command(BaseCommand):
    help = "Seeds initial database records: roles, admin user, locations, and antique categories."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--> Starting Antique Hub database seeding..."))

        # -------------------------------------------------------------
        # 1. Seed Roles
        # -------------------------------------------------------------
        roles_data = ['Admin', 'Seller', 'Buyer']
        roles_dict = {}
        for role_name in roles_data:
            role_obj, created = Role.objects.get_or_create(role=role_name)
            roles_dict[role_name] = role_obj
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Role created: {role_name}"))
            else:
                self.stdout.write(f"  [*] Role exists: {role_name}")

        # -------------------------------------------------------------
        # 2. Seed 3 States, Districts, and Locations
        # -------------------------------------------------------------
        location_hierarchy = {
            'Kerala': {
                'Ernakulam': [
                    'Fort Kochi Heritage Zone',
                    'Mattancherry Jew Town',
                    'Marine Drive Arts Enclave'
                ],
                'Thiruvananthapuram': [
                    'Palayam Heritage Precinct',
                    'Kowdiar Palace Ward'
                ],
            },
            'Rajasthan': {
                'Jaipur': [
                    'Johari Bazaar Craft District',
                    'Hawa Mahal Quarter',
                    'Amer Heritage Corridor'
                ],
                'Udaipur': [
                    'City Palace Road',
                    'Lake Pichola Promenade'
                ],
            },
            'Tamil Nadu': {
                'Chennai': [
                    'Mylapore Temple Ward',
                    'George Town Merchant Quarter'
                ],
                'Madurai': [
                    'Meenakshi Temple Precinct',
                    'South Masi Street'
                ],
            },
        }

        first_state = None
        first_dist = None
        first_loc = None

        for state_name, districts_data in location_hierarchy.items():
            state_obj, _ = State.objects.get_or_create(state=state_name)
            if not first_state:
                first_state = state_obj
            self.stdout.write(self.style.SUCCESS(f"  [+] State: {state_name}"))

            for dist_name, locations_list in districts_data.items():
                dist_obj, _ = District.objects.get_or_create(dist=dist_name, state=state_obj)
                if not first_dist:
                    first_dist = dist_obj
                self.stdout.write(f"      District: {dist_name}")

                for loc_name in locations_list:
                    loc_obj, _ = Location.objects.get_or_create(locname=loc_name, district=dist_obj)
                    if not first_loc:
                        first_loc = loc_obj
                    self.stdout.write(f"          Location: {loc_name}")

        # -------------------------------------------------------------
        # 3. Seed One Admin User & Profile
        # -------------------------------------------------------------
        admin_username = 'admin'
        admin_email = 'admin@antiquehub.com'
        admin_password = 'AdminPassword123!'

        admin_user, user_created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                'email': admin_email,
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'System',
                'last_name': 'Administrator',
            }
        )

        if user_created:
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"  [+] Superuser created: {admin_username} (Password: {admin_password})"))
        else:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(f"  [*] Superuser updated: {admin_username}")

        # Ensure admin UserProfile exists
        admin_role = roles_dict['Admin']
        admin_profile, profile_created = UserProfile.objects.get_or_create(
            login=admin_user,
            defaults={
                'role': admin_role,
                'username': admin_username,
                'contactname': 'Chief Heritage Curator',
                'phone': '9876543210',
                'email': admin_email,
                'address': 'Antique Hub Central HQ, Fort Heritage Zone',
                'state': first_state,
                'district': first_dist,
                'location': first_loc,
                'status': 'Active',
            }
        )
        if profile_created:
            self.stdout.write(self.style.SUCCESS(f"  [+] Admin UserProfile linked: {admin_profile}"))

        # -------------------------------------------------------------
        # 4. Seed 6 Categories & Subcategories
        # -------------------------------------------------------------
        catalog_data = {
            'Furniture': {
                'desc': 'Vintage woodwork, colonial seating, and hand-carved heritage furniture.',
                'subcats': [
                    'Colonial Armchairs',
                    'Teak & Rosewood Writing Desks',
                    'Antique Almirahs & Wardrobes',
                    'Brass-Embossed Chests & Trunks',
                ]
            },
            'Decor': {
                'desc': 'Authentic period accents, wall decor, mirrors, and vintage sculptures.',
                'subcats': [
                    'Vintage Wall Clocks & Pendulums',
                    'Handcrafted Brass & Bronze Statues',
                    'Traditional Persian & Kashmiri Rugs',
                    'Gilded Heritage Wall Mirrors',
                ]
            },
            'Coins': {
                'desc': 'Historical numismatics, ancient dynasties, and imperial currency.',
                'subcats': [
                    'Ancient Mughal & Sultanate Mohurs',
                    'British East India Company Silver Rupees',
                    'Greco-Roman & Kushan Empire Coins',
                    'Princely States Minted Coins',
                ]
            },
            'Jewellery': {
                'desc': 'Timeless adornments, temple jewellery, and antique handcrafted ornaments.',
                'subcats': [
                    'Antique Kundan & Polki Necklaces',
                    'Heritage Temple Gold Bangles',
                    'Victorian Filigree Brooches',
                    'Traditional Navratna Rings',
                ]
            },
            'Artefacts': {
                'desc': 'Archaeological relics, stone sculptures, manuscripts, and tribal art.',
                'subcats': [
                    'Indus Valley Pottery Replicas & Terracotta',
                    'Chola Dynasty Bronze Sculptures',
                    'Antique Palm Leaf Manuscripts',
                    'Tribal Dhokra Brass Sculptures',
                ]
            },
            'Collectibles': {
                'desc': 'Mechanical oddities, vintage technology, nautical instruments, and rare ephemera.',
                'subcats': [
                    'His Masters Voice (HMV) Gramophones',
                    'Vintage Brass Maritime Telescopes',
                    '19th Century Mechanical Pocket Watches',
                    'Classic Folding Cameras',
                ]
            },
        }

        for cat_name, info in catalog_data.items():
            cat_obj, _ = Category.objects.get_or_create(
                category=cat_name,
                defaults={'description': info['desc']}
            )
            self.stdout.write(self.style.SUCCESS(f"  [+] Category: {cat_name}"))

            for subcat_name in info['subcats']:
                subcat_obj, _ = SubCategory.objects.get_or_create(
                    subcategory=subcat_name,
                    category=cat_obj
                )
                self.stdout.write(f"      SubCategory: {subcat_name}")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Antique Hub initial data seeded successfully!"))
        self.stdout.write(self.style.WARNING(f"Admin Credentials -> Username: {admin_username} | Password: {admin_password}"))
