"""
Test suite for Community Module (Module 6 & Module 9 - Comments, Ratings, Moderation, and Watchlist).
Covers:
- Authenticated buyer posting reviews with optional 1 to 5 star rating
- Verified buyer purchase detection (DFD 1.3/DFD 1.4 verification)
- Input sanitization (stripping HTML/script tags)
- Comment length constraints (rejecting < 3 chars and > 1,000 chars)
- Basic profanity filtering (masking offensive words with asterisks and flagging comments)
- Author permissions: author can edit and delete their own comment
- Access control: non-authors blocked from editing or deleting others' comments
- Seller "View Comments": shows reviews on their own items with ratings and filters
- Admin "View Comment": moderation desk with delete option for abusive content
- Watchlist toggle and list view
"""

import io
from decimal import Decimal
from PIL import Image
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from django.db import IntegrityError, transaction
from accounts.models import Role, UserProfile
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock
from django.core.management import call_command
from orders.models import PurchaseMaster, Purchase, Cart
from community.models import Comment, WatchListed, FAQ
from community.utils import sanitize_comment_text, has_user_purchased_item


def create_test_image(filename='antique_comm.jpg', size=(100, 100), color='gold'):
    """Helper to generate in-memory dummy image."""
    file_obj = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')


class Module9CommunityCommentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Roles
        cls.admin_role, _ = Role.objects.get_or_create(role='Admin')
        cls.seller_role, _ = Role.objects.get_or_create(role='Seller')
        cls.buyer_role, _ = Role.objects.get_or_create(role='Buyer')

        # 1. Admin
        cls.admin = User.objects.create_superuser(
            username='admin_comm',
            email='admin@comm.test',
            password='AdminPassword123!'
        )
        cls.admin_profile = UserProfile.objects.create(
            login=cls.admin,
            role=cls.admin_role,
            username='admin_comm',
            contactname='Super Moderator',
            phone='9876543401',
            email='admin@comm.test',
            status='Active'
        )

        # 2. Seller 1 (Owner of Item 1)
        cls.seller = User.objects.create_user(
            username='seller_comm',
            email='seller_comm@test.com',
            password='SellerPassword123!'
        )
        cls.seller_profile = UserProfile.objects.create(
            login=cls.seller,
            role=cls.seller_role,
            username='seller_comm',
            contactname='Heritage Antiques Ltd',
            phone='9876543402',
            email='seller_comm@test.com',
            status='Active'
        )

        # 3. Seller 2 (Owner of Item 2)
        cls.seller2 = User.objects.create_user(
            username='seller2_comm',
            email='seller2_comm@test.com',
            password='SellerPassword123!'
        )
        cls.seller2_profile = UserProfile.objects.create(
            login=cls.seller2,
            role=cls.seller_role,
            username='seller2_comm',
            contactname='Deccan Antiquities',
            phone='9876543403',
            email='seller2_comm@test.com',
            status='Active'
        )

        # 4. Buyer 1 (Purchaser & Reviewer)
        cls.buyer = User.objects.create_user(
            username='buyer_comm',
            email='buyer_comm@test.com',
            password='BuyerPassword123!'
        )
        cls.buyer_profile = UserProfile.objects.create(
            login=cls.buyer,
            role=cls.buyer_role,
            username='buyer_comm',
            contactname='Curator Buyer',
            phone='9876543404',
            email='buyer_comm@test.com',
            status='Active'
        )

        # 5. Buyer 2 (Other user for unauthorized edit/delete tests)
        cls.buyer2 = User.objects.create_user(
            username='buyer2_comm',
            email='buyer2_comm@test.com',
            password='BuyerPassword123!'
        )
        cls.buyer2_profile = UserProfile.objects.create(
            login=cls.buyer2,
            role=cls.buyer_role,
            username='buyer2_comm',
            contactname='Second Collector',
            phone='9876543405',
            email='buyer2_comm@test.com',
            status='Active'
        )

        # Category & SubCategory
        cls.category = Category.objects.create(
            category='Ancient Artefacts',
            description='Sculptures, idols and ritual relics.'
        )
        cls.subcategory = SubCategory.objects.create(
            category=cls.category,
            subcategory='Chola Bronzes'
        )

        # Item 1 (Belongs to Seller 1)
        cls.item = Item.objects.create(
            item='ART-CHOLA-001',
            title='12th Century Chola Bronze Nataraja',
            category=cls.category,
            subcategory=cls.subcategory,
            years_old=850,
            origin='Thanjavur, Chola Dynasty',
            price=125000.00,
            status='Available',
            img1=create_test_image('nataraja.jpg'),
            description='Finely cast bronze icon portraying the cosmic dance of Lord Shiva.',
            seller=cls.seller
        )
        Stock.objects.create(item=cls.item, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Item 2 (Belongs to Seller 2)
        cls.item2 = Item.objects.create(
            item='ART-PANDYAN-002',
            title='14th Century Pandyan Bronze Idol',
            category=cls.category,
            subcategory=cls.subcategory,
            years_old=650,
            origin='Madurai',
            price=80000.00,
            status='Available',
            img1=create_test_image('pandyan.jpg'),
            description='Pandyan bronze sculpture.',
            seller=cls.seller2
        )
        Stock.objects.create(item=cls.item2, tot_arr_stock=1, cur_stock=1, status='In Stock')

        # Create a paid order for Buyer 1 on Item 1 to test verified purchase
        cls.order1 = PurchaseMaster.objects.create(
            buyer=cls.buyer,
            ship_charge=Decimal('0.00'),
            tot_amt=Decimal('125000.00'),
            status='Delivered',
            pay_status='Paid'
        )
        cls.purchase1 = Purchase.objects.create(
            purchase_master=cls.order1,
            item=cls.item,
            quantity=1
        )

    def setUp(self):
        self.client = Client()

    # -------------------------------------------------------------
    # 1. Comment Submission & Ratings Tests
    # -------------------------------------------------------------
    def test_authenticated_buyer_can_add_comment(self):
        """
        Authenticated buyer can submit commentary / review on an antique item.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        response = self.client.post(url, {'comments': 'Remarkable iconography and authentic patina.'})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('catalog:item_detail', kwargs={'item_id': self.item.itemid}))

        comment = Comment.objects.filter(item=self.item, buyer=self.buyer).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.comments, 'Remarkable iconography and authentic patina.')

    def test_post_comment_with_optional_star_rating_and_verified_buyer(self):
        """
        Buyer posts comment with 5-star rating; automatically detects verified purchase.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        payload = {
            'comments': 'Authentic museum-grade sculpture, verified by archaeological carbon patina.',
            'rating': '5'
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 302)

        comment = Comment.objects.filter(item=self.item, buyer=self.buyer).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.rating, 5)
        self.assertTrue(comment.is_verified_buyer)  # Buyer purchased item1
        self.assertFalse(comment.is_flagged)

    def test_unverified_buyer_comment_flags_is_verified_as_false(self):
        """
        Buyer 2 (who has not purchased Item 1) posts a comment; is_verified_buyer is False.
        """
        self.client.login(username='buyer2_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        resp = self.client.post(url, {'comments': 'Inquiring about provenance paperwork before acquiring.', 'rating': '4'})
        self.assertEqual(resp.status_code, 302)

        comment = Comment.objects.filter(item=self.item, buyer=self.buyer2).first()
        self.assertIsNotNone(comment)
        self.assertFalse(comment.is_verified_buyer)
        self.assertEqual(comment.rating, 4)

    def test_add_comment_empty_text_rejected(self):
        """
        Empty comment submission is rejected with an error message and not saved.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        response = self.client.post(url, {'comments': '   '})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(item=self.item).exists())

    def test_add_comment_unauthenticated_redirects_login(self):
        """
        Anonymous user attempting to comment is redirected to login.
        """
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        response = self.client.post(url, {'comments': 'Anonymous comment'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    # -------------------------------------------------------------
    # 2. Sanitization, Length Limit & Profanity Filter Tests
    # -------------------------------------------------------------
    def test_comment_input_sanitization_strips_html_tags(self):
        """
        Input sanitization removes dangerous script and HTML tags to prevent XSS.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        malicious = '<script>alert("hack")</script><b>Gorgeous Chola casting!</b>'
        self.client.post(url, {'comments': malicious})

        comment = Comment.objects.filter(item=self.item, buyer=self.buyer).first()
        self.assertIsNotNone(comment)
        self.assertNotIn('<script>', comment.comments)
        self.assertNotIn('<b>', comment.comments)
        self.assertEqual(comment.comments, 'alert("hack")Gorgeous Chola casting!')

    def test_comment_length_limit_exceeded_rejected(self):
        """
        Comments exceeding 1,000 characters are rejected with an informative error.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        oversized = 'A' * 1050  # Exceeds 1000 char limit
        resp = self.client.post(url, {'comments': oversized})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Comment.objects.filter(item=self.item).exists())

    def test_profanity_filter_masks_abusive_terms_and_flags_comment(self):
        """
        Profanity filter masks abusive words with asterisks and marks is_flagged=True.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        url = reverse('community:add_comment', kwargs={'item_id': self.item.itemid})
        abusive_text = "This relic is a total scam and the seller is an idiot fraudster!"
        self.client.post(url, {'comments': abusive_text})

        comment = Comment.objects.filter(item=self.item, buyer=self.buyer).first()
        self.assertIsNotNone(comment)
        self.assertTrue(comment.is_flagged)
        # Check that words were masked
        self.assertNotIn('scam', comment.comments.lower())
        self.assertNotIn('idiot', comment.comments.lower())
        self.assertIn('s***', comment.comments.lower())
        self.assertIn('i****', comment.comments.lower())

    # -------------------------------------------------------------
    # 3. Author Edit and Delete Tests
    # -------------------------------------------------------------
    def test_author_can_edit_own_comment_and_rating(self):
        """
        Author can update their commentary text and rating.
        """
        comment = Comment.objects.create(
            buyer=self.buyer,
            item=self.item,
            comments='Original initial critique.',
            rating=3
        )
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        edit_url = reverse('community:edit_comment', kwargs={'comment_id': comment.id})

        # 1. GET edit page
        resp_get = self.client.get(edit_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'community/comment_edit.html')

        # 2. POST updated text & rating
        resp_post = self.client.post(edit_url, {
            'comments': 'Updated in-depth appraisal: exceptional casting.',
            'rating': '5'
        })
        self.assertEqual(resp_post.status_code, 302)
        self.assertRedirects(resp_post, reverse('catalog:item_detail', kwargs={'item_id': self.item.itemid}))

        comment.refresh_from_db()
        self.assertEqual(comment.comments, 'Updated in-depth appraisal: exceptional casting.')
        self.assertEqual(comment.rating, 5)

    def test_non_author_blocked_from_editing_comment(self):
        """
        Non-author cannot edit someone else's commentary.
        """
        comment = Comment.objects.create(
            buyer=self.buyer,
            item=self.item,
            comments='Original buyer review.',
            rating=5
        )
        self.client.login(username='buyer2_comm', password='BuyerPassword123!')
        edit_url = reverse('community:edit_comment', kwargs={'comment_id': comment.id})

        resp = self.client.post(edit_url, {'comments': 'Hacked modification', 'rating': '1'})
        self.assertEqual(resp.status_code, 302)

        comment.refresh_from_db()
        self.assertEqual(comment.comments, 'Original buyer review.')

    def test_author_can_delete_own_comment(self):
        """
        Author can delete their own commentary.
        """
        comment = Comment.objects.create(
            buyer=self.buyer,
            item=self.item,
            comments='To be deleted by author.'
        )
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        delete_url = reverse('community:delete_comment', kwargs={'comment_id': comment.id})

        # GET confirmation page
        resp_get = self.client.get(delete_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'community/comment_confirm_delete.html')

        # POST delete
        resp_post = self.client.post(delete_url)
        self.assertEqual(resp_post.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

    def test_non_author_blocked_from_deleting_comment(self):
        """
        Non-author cannot delete another user's commentary.
        """
        comment = Comment.objects.create(
            buyer=self.buyer,
            item=self.item,
            comments='Protected author review.'
        )
        self.client.login(username='buyer2_comm', password='BuyerPassword123!')
        delete_url = reverse('community:delete_comment', kwargs={'comment_id': comment.id})

        resp = self.client.post(delete_url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())

    # -------------------------------------------------------------
    # 4. Seller "View Comments" Tests
    # -------------------------------------------------------------
    def test_seller_view_comments_shows_only_their_items_with_ratings(self):
        """
        Seller sees reviews for their items (Item 1), but not reviews for other sellers' items (Item 2).
        """
        # Comment on Seller 1's item
        c1 = Comment.objects.create(
            buyer=self.buyer,
            item=self.item,
            comments='Magnificent Shiva Nataraja!',
            rating=5
        )
        # Comment on Seller 2's item
        c2 = Comment.objects.create(
            buyer=self.buyer,
            item=self.item2,
            comments='Pandyan sculpture inquiry.',
            rating=4
        )

        self.client.login(username='seller_comm', password='SellerPassword123!')
        seller_comm_url = reverse('community:seller_comments')
        resp = self.client.get(seller_comm_url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'community/seller_comments.html')
        self.assertContains(resp, 'Magnificent Shiva Nataraja!')
        self.assertNotContains(resp, 'Pandyan sculpture inquiry.')
        self.assertEqual(resp.context['avg_rating'], 5.0)

    # -------------------------------------------------------------
    # 5. Admin "View Comment" and Moderation Delete Tests
    # -------------------------------------------------------------
    def test_admin_view_comments_and_delete_abusive_content(self):
        """
        Admin console displays all comments, filters flagged abusive content,
        and provides a delete option to remove abusive reviews.
        """
        c_clean = Comment.objects.create(
            buyer=self.buyer,
            item=self.item,
            comments='Pristine relic!',
            rating=5,
            is_flagged=False
        )
        c_abusive = Comment.objects.create(
            buyer=self.buyer2,
            item=self.item,
            comments='This is a s*** counterfeit piece!',
            rating=1,
            is_flagged=True
        )

        self.client.login(username='admin_comm', password='AdminPassword123!')
        admin_comm_url = reverse('community:admin_comments')

        # 1. Admin sees both comments
        resp_all = self.client.get(admin_comm_url)
        self.assertEqual(resp_all.status_code, 200)
        self.assertContains(resp_all, 'Pristine relic!')
        self.assertContains(resp_all, 'counterfeit piece!')
        self.assertEqual(resp_all.context['flagged_count'], 1)

        # 2. Filter flagged only
        resp_flagged = self.client.get(admin_comm_url, {'flagged': '1'})
        self.assertEqual(resp_flagged.status_code, 200)
        self.assertContains(resp_flagged, 'counterfeit piece!')
        self.assertNotContains(resp_flagged, 'Pristine relic!')

        # 3. Admin deletes abusive comment
        del_url = reverse('community:admin_delete_comment', kwargs={'comment_id': c_abusive.id})
        del_resp = self.client.post(del_url)
        self.assertEqual(del_resp.status_code, 302)
        self.assertRedirects(del_resp, admin_comm_url)

        self.assertFalse(Comment.objects.filter(id=c_abusive.id).exists())
        self.assertTrue(Comment.objects.filter(id=c_clean.id).exists())

    # -------------------------------------------------------------
    # 6. Module 10: Watchlist & DFD 3.0 Reports Tests
    # -------------------------------------------------------------
    def test_toggle_watchlist_add_and_remove(self):
        """
        First toggle adds item to watchlist; second toggle removes it (standard HTTP POST).
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        toggle_url = reverse('community:toggle_watchlist', kwargs={'item_id': self.item.itemid})

        # 1. Add to Watchlist
        resp1 = self.client.post(toggle_url)
        self.assertEqual(resp1.status_code, 302)
        self.assertTrue(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

        # 2. Remove from Watchlist
        resp2 = self.client.post(toggle_url)
        self.assertEqual(resp2.status_code, 302)
        self.assertFalse(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

    def test_ajax_watchlist_heart_toggle(self):
        """
        Asynchronous AJAX request returns JSON with success flag, is_watchlisted boolean,
        updated watchlist_count, item_id, and descriptive confirmation message.
        """
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        toggle_url = reverse('community:toggle_watchlist', kwargs={'item_id': self.item.itemid})

        # 1. AJAX Add
        resp1 = self.client.post(
            toggle_url,
            data={'ajax': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertTrue(data1['success'])
        self.assertTrue(data1['is_watchlisted'])
        self.assertEqual(data1['watchlist_count'], 1)
        self.assertEqual(data1['item_id'], self.item.itemid)
        self.assertIn('added to your personal watchlist', data1['message'])
        self.assertTrue(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

        # 2. AJAX Remove
        resp2 = self.client.post(
            toggle_url,
            data={'ajax': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2['success'])
        self.assertFalse(data2['is_watchlisted'])
        self.assertEqual(data2['watchlist_count'], 0)
        self.assertIn('removed from your personal watchlist', data2['message'])
        self.assertFalse(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

    def test_watchlist_duplicate_prevention_unique_together(self):
        """
        Database uniqueness constraint unique_together = ('user', 'item')
        strictly prevents duplicate records for the same user and relic.
        """
        WatchListed.objects.create(user=self.buyer, item=self.item)

        # Attempting direct duplicate insertion must raise IntegrityError
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                WatchListed.objects.create(user=self.buyer, item=self.item)

        # Only one row exists
        self.assertEqual(WatchListed.objects.filter(user=self.buyer, item=self.item).count(), 1)

    def test_my_watchlist_view_display(self):
        """
        Buyer views "My Watchlist" displaying relic details, formatted price,
        stock availability status, and a "Move to Cart" button.
        """
        WatchListed.objects.create(user=self.buyer, item=self.item)

        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        resp = self.client.get(reverse('community:watchlist_view'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'community/watchlist.html')
        self.assertContains(resp, 'My Curated Watchlist')
        self.assertContains(resp, self.item.title)
        self.assertContains(resp, '125000')
        self.assertContains(resp, 'Available')
        self.assertContains(resp, 'Move to Cart')

    def test_move_to_cart_success(self):
        """
        Buyer clicks "Move to Cart" on an available in-stock relic:
        - Relic is added to the buyer's Cart with quantity 1
        - Relic is deleted from the buyer's WatchListed table
        - Buyer is redirected to the Cart view
        """
        WatchListed.objects.create(user=self.buyer, item=self.item)
        self.assertTrue(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        move_url = reverse('community:move_to_cart', kwargs={'item_id': self.item.itemid})
        resp = self.client.post(move_url)

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('orders:cart_view'))

        # Check cart entry created
        cart_entry = Cart.objects.filter(buyer=self.buyer, item=self.item).first()
        self.assertIsNotNone(cart_entry)
        self.assertEqual(cart_entry.quantity, 1)

        # Check removed from watchlist
        self.assertFalse(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

    def test_move_to_cart_out_of_stock_blocked(self):
        """
        Moving an out-of-stock artifact to cart is rejected with a clear error
        and redirected back to the Watchlist without modifying Cart.
        """
        # Set item to Out of Stock
        self.item.status = 'Out of Stock'
        self.item.save()
        stock = self.item.stock_records.first()
        if stock:
            stock.cur_stock = 0
            stock.status = 'Out of Stock'
            stock.save()

        WatchListed.objects.create(user=self.buyer, item=self.item)

        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        move_url = reverse('community:move_to_cart', kwargs={'item_id': self.item.itemid})
        resp = self.client.post(move_url, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'community/watchlist.html')
        self.assertContains(resp, 'currently out of stock and cannot be moved to cart')
        self.assertFalse(Cart.objects.filter(buyer=self.buyer, item=self.item).exists())
        self.assertTrue(WatchListed.objects.filter(user=self.buyer, item=self.item).exists())

        # Reset item status back to Available
        self.item.status = 'Available'
        self.item.save()
        if stock:
            stock.cur_stock = 1
            stock.status = 'In Stock'
            stock.save()

    def test_move_to_cart_seller_own_item_blocked(self):
        """
        Sellers are blocked from moving their own antique listings into Cart.
        """
        WatchListed.objects.create(user=self.seller, item=self.item)

        self.client.login(username='seller_comm', password='SellerPassword123!')
        move_url = reverse('community:move_to_cart', kwargs={'item_id': self.item.itemid})
        resp = self.client.post(move_url, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'community/watchlist.html')
        self.assertContains(resp, 'You cannot purchase or cart your own antique listing')
        self.assertFalse(Cart.objects.filter(buyer=self.seller, item=self.item).exists())

    def test_admin_watchlist_report_dfd_3_0(self):
        """
        Admin gets "View Watchlist" with most-watched items report (DFD 3.0):
        - Ranked leaderboard of most-monitored relics
        - Summary KPIs: Total entries, Active collectors, Top watched relic, Demand OOS
        - Category, stock status, and search filters
        - Audit trail of recent additions
        """
        # Create watchlist relations:
        # Buyer 1 watches Item 1 & Item 2
        # Buyer 2 watches Item 1
        # => Item 1 has 2 watchers (Rank #1), Item 2 has 1 watcher (Rank #2)
        WatchListed.objects.create(user=self.buyer, item=self.item)
        WatchListed.objects.create(user=self.buyer, item=self.item2)
        WatchListed.objects.create(user=self.buyer2, item=self.item)

        self.client.login(username='admin_comm', password='AdminPassword123!')
        admin_url = reverse('community:admin_watchlist')
        resp = self.client.get(admin_url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'community/admin_watchlist.html')

        # Check KPIs
        self.assertEqual(resp.context['total_watchlist_entries'], 3)
        self.assertEqual(resp.context['unique_watchers_count'], 2)
        self.assertEqual(resp.context['most_watched_item'], self.item)

        # Check items in table
        self.assertContains(resp, self.item.title)
        self.assertContains(resp, self.item2.title)
        self.assertContains(resp, '🥇 #1')
        self.assertContains(resp, '🥈 #2')

        # Test Search Filter
        resp_search = self.client.get(admin_url, {'search': 'Nataraja'})
        self.assertEqual(resp_search.status_code, 200)
        self.assertContains(resp_search, self.item.title)
        self.assertIn(self.item, resp_search.context['page_obj'])
        self.assertNotIn(self.item2, resp_search.context['page_obj'])

        # Test Stock Status Filter
        resp_stock = self.client.get(admin_url, {'stock_status': 'in_stock'})
        self.assertEqual(resp_stock.status_code, 200)
        self.assertContains(resp_stock, self.item.title)

    def test_admin_watchlist_permissions(self):
        """
        Non-admin users (Buyer and Seller) are blocked from accessing Admin Watchlist Report.
        """
        admin_url = reverse('community:admin_watchlist')

        # 1. Unauthenticated redirects to login
        resp_anon = self.client.get(admin_url)
        self.assertEqual(resp_anon.status_code, 302)

        # 2. Buyer blocked
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        resp_buyer = self.client.get(admin_url)
        self.assertEqual(resp_buyer.status_code, 302)

        # 3. Seller blocked
        self.client.login(username='seller_comm', password='SellerPassword123!')
        resp_seller = self.client.get(admin_url)
        self.assertEqual(resp_seller.status_code, 302)

    # -------------------------------------------------------------
    # 7. Module 11: Frequently Asked Questions (FAQ) Tests
    # -------------------------------------------------------------
    def test_seeded_faqs_count_and_topics(self):
        """
        Verifies 8 seeded FAQs exist covering authenticity, shipping, returns, payments, and selling.
        """
        call_command('seed_faqs')
        self.assertEqual(FAQ.objects.count(), 8)

        # Check key topics exist in questions or answers
        all_text = " ".join([f"{f.faq} {f.answer}" for f in FAQ.objects.all()]).lower()
        self.assertIn("authenticity", all_text)
        self.assertIn("shipping", all_text)
        self.assertIn("return", all_text)
        self.assertIn("payment", all_text)
        self.assertIn("seller", all_text)

    def test_public_faq_view_anonymous_buyer_seller(self):
        """
        Public FAQ page is accessible to guests, buyers, and sellers with Bootstrap accordion.
        """
        call_command('seed_faqs')
        faq_url = reverse('community:faq_view')

        # 1. Anonymous visitor
        resp_anon = self.client.get(faq_url)
        self.assertEqual(resp_anon.status_code, 200)
        self.assertTemplateUsed(resp_anon, 'community/faq_list.html')
        self.assertContains(resp_anon, 'Frequently Asked Questions')
        self.assertContains(resp_anon, 'How does Antique Hub verify the authenticity')

        # 2. Authenticated buyer
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        resp_buyer = self.client.get(faq_url)
        self.assertEqual(resp_buyer.status_code, 200)

        # 3. Authenticated seller
        self.client.login(username='seller_comm', password='SellerPassword123!')
        resp_seller = self.client.get(faq_url)
        self.assertEqual(resp_seller.status_code, 200)

    def test_faq_search_keyword(self):
        """
        Search filter checks both question and answer texts and handles empty/no-match states.
        """
        call_command('seed_faqs')
        faq_url = reverse('community:faq_view')

        # Search for shipping
        resp_ship = self.client.get(faq_url, {'q': 'shipping'})
        self.assertEqual(resp_ship.status_code, 200)
        self.assertContains(resp_ship, 'shipping timelines')

        # Search for non-existent keyword
        resp_none = self.client.get(faq_url, {'q': 'extraterrestrial999'})
        self.assertEqual(resp_none.status_code, 200)
        self.assertContains(resp_none, 'No Matching FAQs Found')

    def test_admin_faq_list_and_permissions(self):
        """
        Admin accesses FAQ list table; buyers and sellers are blocked.
        """
        call_command('seed_faqs')
        admin_faq_url = reverse('community:admin_faq_list')

        # 1. Unauthenticated blocked
        self.assertEqual(self.client.get(admin_faq_url).status_code, 302)

        # 2. Buyer blocked
        self.client.login(username='buyer_comm', password='BuyerPassword123!')
        self.assertEqual(self.client.get(admin_faq_url).status_code, 302)

        # 3. Seller blocked
        self.client.login(username='seller_comm', password='SellerPassword123!')
        self.assertEqual(self.client.get(admin_faq_url).status_code, 302)

        # 4. Admin allowed
        self.client.login(username='admin_comm', password='AdminPassword123!')
        resp_admin = self.client.get(admin_faq_url)
        self.assertEqual(resp_admin.status_code, 200)
        self.assertTemplateUsed(resp_admin, 'community/admin_faq_list.html')
        self.assertContains(resp_admin, 'Frequently Asked Questions Management')
        self.assertContains(resp_admin, 'How does Antique Hub verify the authenticity')

    def test_admin_faq_create_valid_and_invalid(self):
        """
        Admin can create a new FAQ, and validation rejects too-short inputs.
        """
        self.client.login(username='admin_comm', password='AdminPassword123!')
        create_url = reverse('community:admin_faq_create')

        # 1. GET form
        resp_get = self.client.get(create_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'community/admin_faq_form.html')

        # 2. POST invalid form
        resp_invalid = self.client.post(create_url, {'faq': 'Why?', 'answer': 'Too short'})
        self.assertEqual(resp_invalid.status_code, 200)
        self.assertFormError(resp_invalid.context['form'], 'faq', 'The FAQ question must be at least 5 characters long.')

        # 3. POST valid form
        resp_valid = self.client.post(create_url, {
            'faq': 'Are physical provenance certificates shipped with bronze idols?',
            'answer': 'Yes, all authenticated bronze sculptures include a signed, physical wax-sealed provenance certificate.'
        })
        self.assertEqual(resp_valid.status_code, 302)
        self.assertRedirects(resp_valid, reverse('community:admin_faq_list'))
        self.assertTrue(FAQ.objects.filter(faq__icontains='bronze idols').exists())

    def test_admin_faq_update(self):
        """
        Admin can edit existing FAQ question and answer.
        """
        faq = FAQ.objects.create(
            faq="Can buyers inspect items in person?",
            answer="Private physical viewings can be scheduled by appointment at our regional vaults."
        )

        self.client.login(username='admin_comm', password='AdminPassword123!')
        update_url = reverse('community:admin_faq_update', kwargs={'faqid': faq.faqid})

        resp_get = self.client.get(update_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, 'Can buyers inspect items in person?')

        resp_post = self.client.post(update_url, {
            'faq': 'Can collectors inspect items in person before purchase?',
            'answer': 'Private physical viewings can be scheduled by appointment at our certified regional heritage vaults.'
        })
        self.assertEqual(resp_post.status_code, 302)
        self.assertRedirects(resp_post, reverse('community:admin_faq_list'))

        faq.refresh_from_db()
        self.assertEqual(faq.faq, 'Can collectors inspect items in person before purchase?')
        self.assertIn('certified regional heritage vaults', faq.answer)

    def test_admin_faq_delete(self):
        """
        Admin can delete an FAQ entry after confirmation.
        """
        faq = FAQ.objects.create(
            faq="Temporary FAQ to be removed soon?",
            answer="This FAQ entry is temporary and intended for deletion verification."
        )

        self.client.login(username='admin_comm', password='AdminPassword123!')
        delete_url = reverse('community:admin_faq_delete', kwargs={'faqid': faq.faqid})

        resp_get = self.client.get(delete_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'community/admin_faq_confirm_delete.html')
        self.assertContains(resp_get, 'Temporary FAQ to be removed soon?')

        resp_post = self.client.post(delete_url)
        self.assertEqual(resp_post.status_code, 302)
        self.assertRedirects(resp_post, reverse('community:admin_faq_list'))
        self.assertFalse(FAQ.objects.filter(faqid=faq.faqid).exists())


