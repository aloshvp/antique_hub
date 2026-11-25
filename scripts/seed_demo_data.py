"""
Module 16: Comprehensive Master Demo Data Seeder for Antique Hub.
Populates all tables in MySQL or SQLite with realistic, production-grade antique data:
- Standard Roles (Admin, Seller, Buyer)
- Geographic Hierarchy (States, Districts, Locations)
- Default Accounts:
    * Administrator: admin / AdminPass123!
    * Verified Sellers: chola_antiques, deccan_relics, rajputana_heritage (Password: SellerPass123!)
    * Pending Seller: malabar_treasures (for testing Admin Activation workflow)
    * Buyers: collector_roy, priya_curator (Password: BuyerPass123!)
- Antique Categories and SubCategories
- Authentic Antique Item Listings with high-resolution imagery and active stock
- Active Category Discounts (Module 12)
- Comprehensive FAQ Knowledge Base (Module 11)
- Simulated Orders, Luhn-authorized Payments, and Tax Invoices (Modules 7 & 8)
- Verified Buyer Reviews with Star Ratings and Profanity Filtering (Module 9)
- Buyer Watchlists (Module 10)

Usage:
    python scripts/seed_demo_data.py
"""

import os
import sys
import io
from decimal import Decimal
from datetime import timedelta
from PIL import Image

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Setup Django Environment
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'antique_hub.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile

from accounts.models import Role, UserProfile
from locations.models import State, District, Location
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock, Discount
from community.models import FAQ, Comment, WatchListed
from orders.models import PurchaseMaster, Purchase
from payments.models import Payment


def create_placeholder_image(filename='antique.jpg', size=(300, 300), color=(180, 140, 60)):
    """Helper to generate dummy antique image bytes."""
    buf = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(buf, format='JPEG', quality=85)
    return ContentFile(buf.getvalue(), name=filename)


def run_seed():
    print("=" * 80)
    print("   ANTIQUE HUB - MODULE 16 MASTER DEMO SEED DATA GENERATOR")
    print("=" * 80)

    # 1. ROLES
    print("\n[1/10] Seeding User Roles (Admin, Seller, Buyer)...")
    admin_role, _ = Role.objects.get_or_create(role='Admin')
    seller_role, _ = Role.objects.get_or_create(role='Seller')
    buyer_role, _ = Role.objects.get_or_create(role='Buyer')
    print("       Roles initialized.")

    # 2. GEOGRAPHIC HIERARCHY
    print("\n[2/10] Seeding Geographic Hierarchy (States, Districts, Locations)...")
    geo_data = {
        'Tamil Nadu': {
            'Thanjavur': ['Brihadisvara Belt', 'Kumbakonam Craft Zone', 'Palace Quarter'],
            'Madurai': ['Meenakshi Temple Zone', 'South Gate Bazaar'],
            'Chennai': ['Mylapore Heritage Precinct', 'George Town Antiques Market'],
        },
        'Kerala': {
            'Ernakulam': ['Fort Kochi Jew Town', 'Mattancherry Palace Road'],
            'Thrissur': ['Vadakkumnathan Heritage Zone', 'Round South Artisans'],
            'Thiruvananthapuram': ['East Fort Heritage Square', 'Kowdiar Royal Avenue'],
        },
        'Karnataka': {
            'Mysuru': ['Palace Enclave', 'Sayyaji Rao Road Antiquities'],
            'Bengaluru': ['Commercial Street Vintage Quarter', 'Malleshwaram Heritage'],
            'Ballari': ['Hampi Ruins Heritage Zone'],
        },
        'Rajasthan': {
            'Jaipur': ['Johari Bazaar Gem Quarter', 'Amer Fort Crafts Precinct', 'Tripolia Bazaar'],
            'Udaipur': ['City Palace Quarter', 'Jagdish Temple Lane'],
            'Jodhpur': ['Clock Tower Vintage Market', 'Mehrangarh Foothills'],
        },
        'West Bengal': {
            'Kolkata': ['Park Street Heritage Suite', 'College Street Antiquities', 'Bowbazar Curios'],
        },
        'Maharashtra': {
            'Mumbai': ['Colaba Causeway Curios', 'Chor Bazaar Heritage Lane', 'Fort Arts District'],
        }
    }

    loc_lookup = {}
    for sname, districts in geo_data.items():
        st_obj, _ = State.objects.get_or_create(state=sname)
        for dname, locations in districts.items():
            dist_obj, _ = District.objects.get_or_create(state=st_obj, dist=dname)
            for lname in locations:
                loc_obj, _ = Location.objects.get_or_create(district=dist_obj, locname=lname)
                loc_lookup[f"{sname}:{dname}:{lname}"] = (st_obj, dist_obj, loc_obj)

    print(f"       Created {State.objects.count()} States, {District.objects.count()} Districts, {Location.objects.count()} Locations.")

    # 3. USERS AND PROFILES
    print("\n[3/10] Seeding Users and User Profiles...")

    # A. Superuser / Administrator
    admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@antiquehub.com'})
    admin_user.set_password('AdminPass123!')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()

    st, dt, lc = loc_lookup['Tamil Nadu:Chennai:Mylapore Heritage Precinct']
    UserProfile.objects.update_or_create(
        login=admin_user,
        defaults={
            'role': admin_role, 'username': 'admin', 'contactname': 'Director of Antiquities (Admin)',
            'phone': '9876543210', 'email': 'admin@antiquehub.com', 'address': 'National Antiquities Commission HQ',
            'state': st, 'district': dt, 'location': lc, 'status': 'Active'
        }
    )

    # B. Verified Sellers
    sellers_data = [
        {
            'username': 'chola_antiques', 'name': 'Thanjavur Royal Antiques Co.', 'email': 'sales@cholaantiques.com',
            'phone': '9876501101', 'addr': '14 Brihadisvara South Street', 'loc_key': 'Tamil Nadu:Thanjavur:Brihadisvara Belt',
            'status': 'Active'
        },
        {
            'username': 'deccan_relics', 'name': 'Deccan Heritage & Numismatics', 'email': 'info@deccanrelics.com',
            'phone': '9876501102', 'addr': '28 Palace Enclave North', 'loc_key': 'Karnataka:Mysuru:Palace Enclave',
            'status': 'Active'
        },
        {
            'username': 'rajputana_heritage', 'name': 'Amer Imperial Armoury & Curios', 'email': 'curios@rajputana.com',
            'phone': '9876501103', 'addr': '88 Johari Bazaar Gate', 'loc_key': 'Rajasthan:Jaipur:Johari Bazaar Gem Quarter',
            'status': 'Active'
        },
        {
            'username': 'malabar_treasures', 'name': 'Malabar Spice Coast Antiquities', 'email': 'contact@malabartreasures.com',
            'phone': '9876501104', 'addr': '10 Jew Town Synagogue Road', 'loc_key': 'Kerala:Ernakulam:Fort Kochi Jew Town',
            'status': 'Pending'  # Intentionally Pending to demonstrate Admin Activation workflow
        },
    ]

    seller_users = {}
    for sinfo in sellers_data:
        usr, _ = User.objects.get_or_create(username=sinfo['username'], defaults={'email': sinfo['email']})
        usr.set_password('SellerPass123!')
        usr.save()
        st, dt, lc = loc_lookup[sinfo['loc_key']]
        UserProfile.objects.update_or_create(
            login=usr,
            defaults={
                'role': seller_role, 'username': sinfo['username'], 'contactname': sinfo['name'],
                'phone': sinfo['phone'], 'email': sinfo['email'], 'address': sinfo['addr'],
                'state': st, 'district': dt, 'location': lc, 'status': sinfo['status']
            }
        )
        seller_users[sinfo['username']] = usr

    # C. Registered Buyers
    buyers_data = [
        {
            'username': 'collector_roy', 'name': 'Roy Vintage Collector', 'email': 'roy.vintage@curators.in',
            'phone': '9876502201', 'addr': '44 Park Street Heritage Suite', 'loc_key': 'West Bengal:Kolkata:Park Street Heritage Suite'
        },
        {
            'username': 'priya_curator', 'name': 'Priya Art Historian', 'email': 'priya.curator@heritage.org',
            'phone': '9876502202', 'addr': '102 Indiranagar 12th Main', 'loc_key': 'Karnataka:Bengaluru:Malleshwaram Heritage'
        },
    ]

    buyer_users = {}
    for binfo in buyers_data:
        usr, _ = User.objects.get_or_create(username=binfo['username'], defaults={'email': binfo['email']})
        usr.set_password('BuyerPass123!')
        usr.save()
        st, dt, lc = loc_lookup[binfo['loc_key']]
        UserProfile.objects.update_or_create(
            login=usr,
            defaults={
                'role': buyer_role, 'username': binfo['username'], 'contactname': binfo['name'],
                'phone': binfo['phone'], 'email': binfo['email'], 'address': binfo['addr'],
                'state': st, 'district': dt, 'location': lc, 'status': 'Active'
            }
        )
        buyer_users[binfo['username']] = usr

    print(f"       Provisioned {User.objects.count()} Users (Admin, 4 Sellers, 2 Buyers).")

    # 4. CATEGORIES & SUBCATEGORIES
    print("\n[4/10] Seeding Antique Categories and SubCategories...")
    cats_data = [
        ('Coins & Numismatics', 'Ancient and medieval imperial coinage from Indian dynasties and the Silk Road.', [
            'Chola Dynasty', 'Mughal Empire', 'Pandyan Dynasty', 'British East India Company'
        ]),
        ('Sacred Bronzes', 'Lost-wax cast sacred iconography, deity murtis, and devotional temple artifacts.', [
            'Chola Bronzes', 'Hoysala Idols', 'Temple Deepams & Bells', 'Ritual Urulis'
        ]),
        ('Royal Armour & Weapons', 'Damascened steel weaponry, jewelled hilts, and ceremonial royal parade armaments.', [
            'Mughal Damascene Daggers', 'Rajput Talwars & Pesh-Kabz', 'Ceremonial Shields'
        ]),
        ('Vintage Furniture & Decor', 'Colonial, regal palace, and teak/rosewood heritage cabinetry and furnishings.', [
            'Dutch Colonial Teak Desks', 'Carved Rosewood Chests', 'Plantation Armchairs'
        ]),
        ('Antiquarian Carpets & Textiles', 'Hand-knotted silk rugs, gold-thread brocades, and historic court shawls.', [
            'Kashmiri Silk Carpets', 'Zardozi Embroidered Silks', 'Pashmina Heritage Shawls'
        ]),
    ]

    cat_map = {}
    subcat_map = {}
    for ctitle, cdesc, sublist in cats_data:
        cobj, _ = Category.objects.get_or_create(category=ctitle, defaults={'description': cdesc})
        cat_map[ctitle] = cobj
        for stitle in sublist:
            sobj, _ = SubCategory.objects.get_or_create(category=cobj, subcategory=stitle)
            subcat_map[f"{ctitle}:{stitle}"] = sobj

    print(f"       Created {Category.objects.count()} Categories and {SubCategory.objects.count()} SubCategories.")

    # 5. CATALOG ITEMS & INVENTORY STOCKS
    print("\n[5/10] Seeding Authentic Antique Item Listings & Stock Records...")
    items_seed = [
        {
            'code': 'CHOLA-NATARAJA-1050',
            'title': '10th Century Chola Lost-Wax Bronze Shiva Nataraja',
            'cat': 'Sacred Bronzes', 'subcat': 'Chola Bronzes',
            'seller': seller_users['chola_antiques'],
            'price': Decimal('240000.00'), 'years_old': 980, 'origin': 'Thanjavur Royal Foundry, Chola Empire',
            'desc': 'Magnificent lost-wax casting depicting Nataraja dancing within an aureole of cosmic fire (Prabha Mandala). Rich greenish-black authentic patina verified through spectroscopic analysis.',
            'stock': 3, 'img_name': 'nataraja1.jpg'
        },
        {
            'code': 'MUGHAL-DAGGER-1680',
            'title': '17th Century Mughal Jade-Hilt Damascene Dagger (Khanjar)',
            'cat': 'Royal Armour & Weapons', 'subcat': 'Mughal Damascene Daggers',
            'seller': seller_users['rajputana_heritage'],
            'price': Decimal('165000.00'), 'years_old': 345, 'origin': 'Delhi Imperial Armoury, Mughal Court',
            'desc': 'Curved double-edged wootz crucible steel blade with damascened gold koftgari inlay. The hilt is carved from pale mutton-fat nephrite jade terminating in a sculpted horse head.',
            'stock': 2, 'img_name': 'mughal_dagger.jpg'
        },
        {
            'code': 'CHOLA-KAHAVANU-990',
            'title': 'Raja Raja Chola I Gold Kahavanu Coin (10th C.)',
            'cat': 'Coins & Numismatics', 'subcat': 'Chola Dynasty',
            'seller': seller_users['deccan_relics'],
            'price': Decimal('48000.00'), 'years_old': 1030, 'origin': 'Gangaikonda Cholapuram Mint',
            'desc': 'Exceptional grade uncirculated gold kahavanu showing king standing holding lotus on obverse, seated king holding conch on reverse. Weight: 4.3 grams. Certificate of authenticity included.',
            'stock': 5, 'img_name': 'coin1.jpg'
        },
        {
            'code': 'PANDYAN-FISH-SILVER',
            'title': '13th Century Pandyan Dynasty Silver Drachm (Twin Fish Emblem)',
            'cat': 'Coins & Numismatics', 'subcat': 'Pandyan Dynasty',
            'seller': seller_users['deccan_relics'],
            'price': Decimal('18500.00'), 'years_old': 750, 'origin': 'Madurai Royal Mint',
            'desc': 'Rare Pandyan silver denomination depicting the sacred twin carp emblem flanked by royal parasol and flywhisks. Excellent strike and high relief.',
            'stock': 6, 'img_name': 'pandyan.jpg'
        },
        {
            'code': 'RAJPUT-TALWAR-1750',
            'title': '18th Century Rajput Royal Court Talwar Sword',
            'cat': 'Royal Armour & Weapons', 'subcat': 'Rajput Talwars & Pesh-Kabz',
            'seller': seller_users['rajputana_heritage'],
            'price': Decimal('89000.00'), 'years_old': 275, 'origin': 'Mewar Kingdom, Rajasthan',
            'desc': 'Traditional curved high-carbon steel blade with disc pommel hilt adorned with intricate floral gold damascening. Fitted in original velvet-covered wooden scabbard with pierced brass chape.',
            'stock': 3, 'img_name': 'talwar1.jpg'
        },
        {
            'code': 'TEMPLE-DEEPAM-BRONZE',
            'title': '19th Century Sacred Mayur Temple Oil Lamp (Deepam)',
            'cat': 'Sacred Bronzes', 'subcat': 'Temple Deepams & Bells',
            'seller': seller_users['chola_antiques'],
            'price': Decimal('32000.00'), 'years_old': 160, 'origin': 'Kumbakonam Temple Belt',
            'desc': 'Heavy solid cast bronze tiered ceremonial oil lamp surmounted by a gracefully sculpted peacock (Mayura). Five-wick oil reservoir with dark sacred temple patina.',
            'stock': 4, 'img_name': 'lamp1.jpg'
        },
        {
            'code': 'KERALA-URLI-BELLMETAL',
            'title': 'Heritage Traditional Bell-Metal Cooking Uruli Vessel',
            'cat': 'Sacred Bronzes', 'subcat': 'Ritual Urulis',
            'seller': seller_users['chola_antiques'],
            'price': Decimal('26000.00'), 'years_old': 140, 'origin': 'Mannar Bell Metal Artisans, Kerala',
            'desc': 'Masterfully cast heavy acoustic bell-metal uruli with dual cast loop handles. Resonates with deep chime when struck; ideal for heritage decor or floating water flowers.',
            'stock': 4, 'img_name': 'urli.jpg'
        },
        {
            'code': 'COLONIAL-ROSEWOOD-BOX',
            'title': '19th Century Anglo-Indian Brass-Inlaid Rosewood Treasure Box',
            'cat': 'Vintage Furniture & Decor', 'subcat': 'Carved Rosewood Chests',
            'seller': seller_users['deccan_relics'],
            'price': Decimal('42000.00'), 'years_old': 155, 'origin': 'Malabar Coast Trading Post',
            'desc': 'Lustrous aged Malabar rosewood fitted with hand-chiseled pierced brass corners, strapwork hinges, and hidden compartment. Key included with original lock mechanism.',
            'stock': 2, 'img_name': 'box1.jpg'
        },
        {
            'code': 'KASHMIR-SILK-CARPET-1920',
            'title': 'Vintage Hand-Knotted Kashmiri Pure Silk Hunting Carpet (Shikargah)',
            'cat': 'Antiquarian Carpets & Textiles', 'subcat': 'Kashmiri Silk Carpets',
            'seller': seller_users['rajputana_heritage'],
            'price': Decimal('135000.00'), 'years_old': 105, 'origin': 'Srinagar Weavers Guild, Kashmir',
            'desc': 'Superfine master weaver carpet featuring 650 knots per square inch. Shikargah hunting motif with natural vegetable dyes including madder, saffron, and indigo.',
            'stock': 1, 'img_name': 'carpet1.jpg'
        },
        {
            'code': 'COLONIAL-TEAK-PLANTER',
            'title': '19th Century British East India Teakwood Planters Chair',
            'cat': 'Vintage Furniture & Decor', 'subcat': 'Plantation Armchairs',
            'seller': seller_users['chola_antiques'],
            'price': Decimal('58000.00'), 'years_old': 130, 'origin': 'Nilgiri Tea Estates Bungalow',
            'desc': 'Authentic colonial plantation chair crafted from old-growth Burma teak with original hand-woven cane webbing and fold-out leg extensions.',
            'stock': 2, 'img_name': 'chair.jpg'
        },
    ]

    for idata in items_seed:
        c_obj = cat_map[idata['cat']]
        s_obj = subcat_map[f"{idata['cat']}:{idata['subcat']}"]
        img_file = create_placeholder_image(filename=idata['img_name'])

        item_obj, _ = Item.objects.update_or_create(
            item=idata['code'],
            defaults={
                'seller': idata['seller'],
                'title': idata['title'],
                'category': c_obj,
                'subcategory': s_obj,
                'years_old': idata['years_old'],
                'origin': idata['origin'],
                'description': idata['desc'],
                'price': idata['price'],
                'status': 'Available',
                'img1': img_file,
            }
        )

        Stock.objects.update_or_create(
            item=item_obj,
            defaults={
                'tot_arr_stock': idata['stock'],
                'cur_stock': idata['stock'],
                'stockdate': timezone.now(),
                'status': 'Available'
            }
        )

    print(f"       Provisioned {Item.objects.count()} Unique Artifact Listings with Stock.")

    # 6. PROMOTIONAL DISCOUNTS (Module 12)
    print("\n[6/10] Seeding Active Promotional Category Discounts...")
    now = timezone.now().date()
    Discount.objects.update_or_create(
        applicable_cat=cat_map['Coins & Numismatics'],
        defaults={
            'discount_percent': Decimal('15.00'),
            'startdate': now - timedelta(days=5),
            'enddate': now + timedelta(days=25),
        }
    )
    Discount.objects.update_or_create(
        applicable_cat=cat_map['Sacred Bronzes'],
        defaults={
            'discount_percent': Decimal('10.00'),
            'startdate': now - timedelta(days=2),
            'enddate': now + timedelta(days=30),
        }
    )
    print(f"       Created {Discount.objects.count()} Category Promotional Discounts.")

    # 7. FREQUENTLY ASKED QUESTIONS (Module 11)
    print("\n[7/10] Seeding FAQ Knowledge Base Accordion...")
    faqs_data = [
        ("How does Antique Hub verify the authenticity and provenance of antique items?",
         "Every listing on Antique Hub is subject to rigorous provenance screening. Sellers are required to upload high-resolution multi-angle photographs, hallmarks, microscopic patina examinations, and existing archaeological or family lineage certificates. Our curated inspection guidelines adhere to Indian Antiquities and Art Treasures Act norms.",
         "Authenticity"),
        ("What payment methods are supported on the platform?",
         "Antique Hub supports major Credit Cards (Visa, MasterCard, RuPay, American Express) validated via the Modulo-10 Luhn algorithm, Debit Cards, Net Banking from leading scheduled banks, and Cash on Delivery (COD) for domestic buyers. All payment handling is strictly PCI-DSS compliant.",
         "Payments"),
        ("How are fragile and high-value antique artifacts shipped?",
         "Items are packaged using museum-grade shock-absorbing foam, custom wooden archival crates, and climate-sealed packaging. Every shipment is fully insured up to the purchase valuation and transported via high-security tracked express couriers.",
         "Shipping"),
        ("What is the return and refund policy for antique collectors?",
         "Buyers have a 7-day inspection window upon delivery. If an item is demonstrated to diverge materially from the catalog description or fail metallurgical verification, a full refund is processed upon return of the item in its unaltered original state.",
         "Returns"),
        ("How do I become an approved Seller on Antique Hub?",
         "Prospective sellers register through the portal with their business registration, government identification, and geographic location. Accounts remain in 'Pending' status until our Administrator conducts background verification and activates the seller profile.",
         "Selling"),
        ("Can sellers purchase their own antique items?",
         "No. Antique Hub enforces strict marketplace integrity rules. Buyers are prevented from adding or purchasing listings uploaded from their own seller accounts to stop wash-trading and artificial price inflation.",
         "Security"),
        ("How are promotional discounts applied to antique orders?",
         "Active promotional discounts are applied on a category-wide basis by the Administrator. The effective price is computed uniformly across the marketplace catalogue, product detail pages, shopping cart, and final checkout.",
         "Discounts"),
        ("Is full credit card information stored on the server?",
         "Never. Under PCI-DSS compliance regulations, Antique Hub never stores primary account numbers (PAN) or CVV codes. Only the last 4 digits, detected card network (e.g. Visa), issuing bank, and gateway transaction reference ID are retained.",
         "Payments"),
    ]

    for q, a, cat in faqs_data:
        FAQ.objects.update_or_create(faq=q, defaults={'answer': a})

    print(f"       Provisioned {FAQ.objects.count()} Curated FAQs.")

    # 8. DEMO ORDERS & PAYMENTS (Modules 7 & 8)
    print("\n[8/10] Seeding Historical Orders, Luhn-Validated Payments & Tax Invoices...")
    sample_item1 = Item.objects.get(item='CHOLA-KAHAVANU-990')
    sample_item2 = Item.objects.get(item='KERALA-URLI-BELLMETAL')

    # Order 1: Paid Credit Card Order
    order1, _ = PurchaseMaster.objects.update_or_create(
        buyer=buyer_users['collector_roy'],
        defaults={
            'ship_charge': Decimal('0.00'),
            'tot_amt': Decimal('40800.00'),  # Discounted 15% from 48,000
            'status': 'Confirmed',
            'pay_status': 'Paid'
        }
    )
    Purchase.objects.update_or_create(
        purchase_master=order1, item=sample_item1,
        defaults={'quantity': 1, 'price': Decimal('40800.00')}
    )
    Payment.objects.update_or_create(
        purchase_master=order1,
        defaults={
            'buyer': buyer_users['collector_roy'],
            'amount': Decimal('40800.00'),
            'method': 'Credit Card',
            'status': 'Success',
            'card_last4': '4242',
            'card_type': 'Visa',
            'bank_name': 'HDFC Bank',
            'transaction_ref': 'TXN-AH-DEMO-20261020-001'
        }
    )

    # Order 2: Shipped Order
    order2, _ = PurchaseMaster.objects.update_or_create(
        buyer=buyer_users['priya_curator'],
        defaults={
            'ship_charge': Decimal('250.00'),
            'tot_amt': Decimal('23650.00'),  # 23,400 + 250 shipping
            'status': 'Shipped',
            'pay_status': 'Paid'
        }
    )
    Purchase.objects.update_or_create(
        purchase_master=order2, item=sample_item2,
        defaults={'quantity': 1, 'price': Decimal('23400.00')}
    )
    Payment.objects.update_or_create(
        purchase_master=order2,
        defaults={
            'buyer': buyer_users['priya_curator'],
            'amount': Decimal('23650.00'),
            'method': 'Debit Card',
            'status': 'Success',
            'card_last4': '1111',
            'card_type': 'Visa',
            'bank_name': 'State Bank of India',
            'transaction_ref': 'TXN-AH-DEMO-20261020-002'
        }
    )

    print(f"       Created {PurchaseMaster.objects.count()} Orders, {Purchase.objects.count()} Purchase Line Items, {Payment.objects.count()} Payment Records.")

    # 9. COMMENTS & REVIEWS (Module 9)
    print("\n[9/10] Seeding Verified Buyer Comments & Ratings...")
    Comment.objects.update_or_create(
        buyer=buyer_users['collector_roy'],
        item=sample_item1,
        defaults={
            'comments': "Exceptional Raja Raja Chola gold kahavanu! The weight and patina are perfectly consistent with Thanjavur museum specimens. Shipped in tamper-proof archival casing with full documentation.",
            'rating': 5,
            'is_verified_buyer': True,
            'is_flagged': False
        }
    )
    Comment.objects.update_or_create(
        buyer=buyer_users['priya_curator'],
        item=sample_item2,
        defaults={
            'comments': "Magnificent acoustic bell metal uruli. Resonates cleanly and exhibits authentic 19th century hand-hammered surface marks. Very satisfied with the seller's transparency.",
            'rating': 5,
            'is_verified_buyer': True,
            'is_flagged': False
        }
    )
    print(f"       Created {Comment.objects.count()} Verified Buyer Reviews.")

    # 10. WATCHLIST ITEMS (Module 10)
    print("\n[10/10] Seeding Buyer Watchlist Records...")
    nataraja_item = Item.objects.get(item='CHOLA-NATARAJA-1050')
    dagger_item = Item.objects.get(item='MUGHAL-DAGGER-1680')

    WatchListed.objects.update_or_create(user=buyer_users['collector_roy'], item=nataraja_item)
    WatchListed.objects.update_or_create(user=buyer_users['priya_curator'], item=dagger_item)
    print(f"       Created {WatchListed.objects.count()} Watchlist Entries.")

    print("\n" + "=" * 80)
    print("   \033[1;32m[SUCCESS] MASTER DEMO SEED DATA GENERATION COMPLETE!\033[0m")
    print("=" * 80)
    print("\nDefault Demo Login Credentials:")
    print("  Administrator : admin               / AdminPass123!")
    print("  Seller 1      : chola_antiques      / SellerPass123! (Active)")
    print("  Seller 2      : deccan_relics       / SellerPass123! (Active)")
    print("  Seller 3      : rajputana_heritage  / SellerPass123! (Active)")
    print("  Seller 4      : malabar_treasures   / SellerPass123! (Pending Approval)")
    print("  Buyer 1       : collector_roy       / BuyerPass123!")
    print("  Buyer 2       : priya_curator       / BuyerPass123!")
    print("=" * 80)


if __name__ == '__main__':
    run_seed()
