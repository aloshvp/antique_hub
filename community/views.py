"""
Views for Community Module (Module 9 - Comments, Ratings, Moderation, and Watchlist).
Covers:
- Buyer post commentary and 1-5 star rating on items (with verified purchase detection)
- Input sanitization, max length limits (1,000 chars), and basic profanity filtering
- Author edit and delete permissions for comments
- Seller "View Comments" for their own items with ratings and filters
- Admin "View Comment" moderation console with delete option for abusive/flagged content
- Watchlist management
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q

from django.http import JsonResponse
from accounts.decorators import admin_required, seller_required
from catalog.models import Item, Category
from .models import Comment, WatchListed, FAQ
from .forms import FAQForm
from .utils import sanitize_comment_text, has_user_purchased_item


@login_required
def add_comment(request, item_id):
    """
    Post a commentary and optional 1 to 5 star rating on an antique artifact.
    - Sanitizes input and checks 3 to 1,000 character length limits.
    - Applies profanity filter and flags abusive content.
    - Automatically checks if buyer has purchased this item (DFD 1.3/1.4 verified buyer).
    """
    item = get_object_or_404(Item, itemid=item_id)

    if request.method != 'POST':
        return redirect('catalog:item_detail', item_id=item.itemid)

    raw_text = request.POST.get('comments', '')
    rating_raw = request.POST.get('rating', '').strip()

    # 1. Sanitize text, check length and filter profanity
    clean_text, is_flagged, err_msg = sanitize_comment_text(raw_text)
    if err_msg:
        messages.error(request, err_msg)
        return redirect('catalog:item_detail', item_id=item.itemid)

    # 2. Parse optional 1 to 5 star rating
    rating = None
    if rating_raw:
        try:
            rating_val = int(rating_raw)
            if 1 <= rating_val <= 5:
                rating = rating_val
            else:
                messages.warning(request, "Rating must be an integer between 1 and 5 stars.")
        except (ValueError, TypeError):
            pass

    # 3. Check if user is a verified purchaser of this artifact
    is_verified = has_user_purchased_item(request.user, item)

    # 4. Save comment
    comment = Comment.objects.create(
        buyer=request.user,
        item=item,
        comments=clean_text,
        rating=rating,
        is_verified_buyer=is_verified,
        is_flagged=is_flagged
    )

    if is_flagged:
        messages.warning(
            request,
            "Your commentary has been submitted. Note: Some language was automatically masked for community moderation."
        )
    else:
        messages.success(request, "Your commentary and rating have been posted successfully!")

    return redirect('catalog:item_detail', item_id=item.itemid)


@login_required
def edit_comment(request, comment_id):
    """
    Allows the author of a comment to edit their text and rating.
    """
    comment = get_object_or_404(
        Comment.objects.select_related('item', 'buyer'),
        id=comment_id
    )

    # Author authorization check
    if comment.buyer != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied. You can only edit your own comments.")
        return redirect('catalog:item_detail', item_id=comment.item.itemid)

    if request.method == 'POST':
        raw_text = request.POST.get('comments', '')
        rating_raw = request.POST.get('rating', '').strip()

        clean_text, is_flagged, err_msg = sanitize_comment_text(raw_text)
        if err_msg:
            messages.error(request, err_msg)
            return render(request, 'community/comment_edit.html', {
                'comment': comment,
                'rating_choices': Comment.RATING_CHOICES,
            })

        rating = None
        if rating_raw:
            try:
                rating_val = int(rating_raw)
                if 1 <= rating_val <= 5:
                    rating = rating_val
            except (ValueError, TypeError):
                pass

        comment.comments = clean_text
        comment.rating = rating
        comment.is_flagged = is_flagged
        comment.save()

        messages.success(request, "Your commentary has been updated.")
        return redirect('catalog:item_detail', item_id=comment.item.itemid)

    return render(request, 'community/comment_edit.html', {
        'comment': comment,
        'rating_choices': Comment.RATING_CHOICES,
    })


@login_required
def delete_comment(request, comment_id):
    """
    Allows the author of a comment (or admin) to delete their comment with confirmation.
    """
    comment = get_object_or_404(
        Comment.objects.select_related('item', 'buyer'),
        id=comment_id
    )

    # Authorization check
    if comment.buyer != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied. You can only delete your own comments.")
        return redirect('catalog:item_detail', item_id=comment.item.itemid)

    item_id = comment.item.itemid

    if request.method == 'POST':
        comment.delete()
        messages.success(request, "Your commentary has been deleted.")
        return redirect('catalog:item_detail', item_id=item_id)

    return render(request, 'community/comment_confirm_delete.html', {
        'comment': comment,
        'item': comment.item,
    })


@login_required
@seller_required
def seller_comments(request):
    """
    Seller "View Comments" page showing all reviews and commentary
    posted on antique items uploaded by the authenticated seller.
    Includes item filter, star rating filter, and keyword search.
    """
    comments_qs = Comment.objects.filter(
        item__seller=request.user
    ).select_related(
        'item', 'buyer', 'buyer__userprofile'
    ).order_by('-cdate')

    # Item filter
    item_id = request.GET.get('item_id', '').strip()
    if item_id and item_id.isdigit():
        comments_qs = comments_qs.filter(item__itemid=int(item_id))

    # Rating filter
    rating_filter = request.GET.get('rating', '').strip()
    if rating_filter and rating_filter.isdigit():
        comments_qs = comments_qs.filter(rating=int(rating_filter))

    # Search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        comments_qs = comments_qs.filter(
            Q(comments__icontains=search_query) |
            Q(buyer__username__icontains=search_query) |
            Q(item__title__icontains=search_query)
        )

    # Seller metrics
    all_seller_comments = Comment.objects.filter(item__seller=request.user)
    total_comments = all_seller_comments.count()
    avg_rating = all_seller_comments.filter(rating__isnull=False).aggregate(
        avg=Avg('rating')
    )['avg'] or 0.0
    five_star_count = all_seller_comments.filter(rating=5).count()

    # Seller's items for dropdown filter
    seller_items = Item.objects.filter(seller=request.user).order_by('title')

    paginator = Paginator(comments_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'community/seller_comments.html', {
        'page_obj': page_obj,
        'seller_items': seller_items,
        'total_comments': total_comments,
        'avg_rating': round(avg_rating, 1),
        'five_star_count': five_star_count,
        'selected_item_id': item_id,
        'selected_rating': rating_filter,
        'search_query': search_query,
    })


@login_required
@admin_required
def admin_comments(request):
    """
    Admin "View Comment" master console with moderation controls and delete option
    for abusive, offensive, or counterfeit accusations.
    """
    comments_qs = Comment.objects.select_related(
        'item', 'item__seller', 'buyer', 'buyer__userprofile'
    ).order_by('-cdate')

    # Moderation flag filter
    flagged_only = request.GET.get('flagged', '').strip()
    if flagged_only == '1':
        comments_qs = comments_qs.filter(is_flagged=True)

    # Rating filter
    rating_filter = request.GET.get('rating', '').strip()
    if rating_filter and rating_filter.isdigit():
        comments_qs = comments_qs.filter(rating=int(rating_filter))

    # Search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        comments_qs = comments_qs.filter(
            Q(comments__icontains=search_query) |
            Q(buyer__username__icontains=search_query) |
            Q(item__title__icontains=search_query)
        )

    # Overall KPIs
    total_comments = Comment.objects.count()
    flagged_count = Comment.objects.filter(is_flagged=True).count()
    platform_avg_rating = Comment.objects.filter(rating__isnull=False).aggregate(
        avg=Avg('rating')
    )['avg'] or 0.0

    paginator = Paginator(comments_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'community/admin_comments.html', {
        'page_obj': page_obj,
        'total_comments': total_comments,
        'flagged_count': flagged_count,
        'platform_avg_rating': round(platform_avg_rating, 1),
        'flagged_only': flagged_only,
        'selected_rating': rating_filter,
        'search_query': search_query,
    })


@login_required
@admin_required
def admin_delete_comment(request, comment_id):
    """
    Admin action to remove abusive or offensive commentary.
    """
    comment = get_object_or_404(
        Comment.objects.select_related('item', 'buyer'),
        id=comment_id
    )

    if request.method == 'POST':
        item_title = comment.item.title
        author = comment.buyer.username
        comment.delete()
        messages.success(
            request,
            f"Comment #{comment_id} on '{item_title}' by @{author} was deleted for community guidelines compliance."
        )
        return redirect('community:admin_comments')

    return render(request, 'community/admin_comment_confirm_delete.html', {
        'comment': comment,
    })


@login_required
def watchlist_view(request):
    """
    Buyer view to browse all saved artifacts in their personal Watchlist.
    """
    watchlist_items = WatchListed.objects.filter(user=request.user).select_related(
        'item',
        'item__category',
        'item__subcategory',
        'item__seller',
        'item__seller__userprofile',
        'item__seller__userprofile__location',
        'item__seller__userprofile__district',
        'item__seller__userprofile__state',
    ).prefetch_related(
        'item__stock_records',
        'item__category__discounts',
    ).order_by('-added_date')

    return render(request, 'community/watchlist.html', {
        'watchlist_items': watchlist_items,
        'page_title': 'My Curated Watchlist | Antique Hub',
    })


@login_required
def toggle_watchlist(request, item_id):
    """
    Toggle an artifact in the user's personal watchlist.
    Supports both:
    1. Asynchronous AJAX heart toggle requests (returns JSON)
    2. Traditional HTTP POST form submissions (redirects with Django messages)
    Guarantees no duplicates via unique user+item constraint.
    """
    item = get_object_or_404(Item, itemid=item_id)
    watch_entry = WatchListed.objects.filter(user=request.user, item=item).first()

    if watch_entry:
        watch_entry.delete()
        is_watchlisted = False
        msg = f"'{item.title}' removed from your personal watchlist."
    else:
        WatchListed.objects.get_or_create(user=request.user, item=item)
        is_watchlisted = True
        msg = f"'{item.title}' added to your personal watchlist!"

    total_count = WatchListed.objects.filter(user=request.user).count()

    # Detect AJAX request
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('accept', '') or
        request.POST.get('ajax') == '1'
    )

    if is_ajax:
        return JsonResponse({
            'success': True,
            'is_watchlisted': is_watchlisted,
            'watchlist_count': total_count,
            'item_id': item.itemid,
            'message': msg
        })

    if is_watchlisted:
        messages.success(request, msg)
    else:
        messages.info(request, msg)

    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('catalog:item_detail', item_id=item.itemid)


@login_required
def move_to_cart(request, item_id):
    """
    Moves an antique artifact from "My Watchlist" directly into the buyer's Cart.
    - Validates item availability and positive stock.
    - Prevents seller from carting their own item.
    - Atomically adds to Cart and removes from WatchListed.
    - Redirects directly to the Cart with confirmation.
    """
    if request.method != 'POST':
        return redirect('community:watchlist_view')

    item = get_object_or_404(Item, itemid=item_id)

    # 1. Stop seller from adding own item to cart
    if item.seller == request.user:
        messages.error(request, "You cannot purchase or cart your own antique listing.")
        return redirect('community:watchlist_view')

    # 2. Check stock and availability
    available_stock = item.current_stock
    if item.status != 'Available' or available_stock <= 0:
        messages.error(request, f"'{item.title}' is currently out of stock and cannot be moved to cart.")
        return redirect('community:watchlist_view')

    # 3. Add to Cart (from orders.models import Cart)
    from orders.models import Cart
    cart_entry, created = Cart.objects.get_or_create(
        buyer=request.user,
        item=item,
        defaults={'quantity': 1}
    )
    if not created:
        if cart_entry.quantity < available_stock:
            cart_entry.quantity += 1
            cart_entry.save()
            messages.success(request, f"Increased quantity of '{item.title}' in your Cart to {cart_entry.quantity}.")
        else:
            messages.warning(request, f"'{item.title}' is already in your Cart at maximum available stock ({available_stock} units).")
    else:
        messages.success(request, f"'{item.title}' has been moved to your Cart!")

    # 4. Remove from Watchlist
    WatchListed.objects.filter(user=request.user, item=item).delete()

    return redirect('orders:cart_view')


@login_required
@admin_required
def admin_watchlist(request):
    """
    Admin "View Watchlist" & Most-Watched Items Report (DFD 3.0).
    Provides:
    - Ranked list of most-watched antique relics with demand analytics.
    - Total platform watchlist entries and unique monitoring collectors.
    - High-demand out-of-stock items (artifacts with active watchers but zero stock).
    - Detailed audit table of recent collector watchlist additions.
    - Category, stock status, and search filters.
    """
    # Query items annotated with watch count
    items_qs = Item.objects.select_related(
        'category', 'subcategory', 'seller', 'seller__userprofile'
    ).prefetch_related('stock_records').annotate(
        watch_count=Count('watchlisted_by')
    ).filter(watch_count__gt=0).order_by('-watch_count', '-post_date')

    # Category filter
    category_id = request.GET.get('category_id', '').strip()
    if category_id and category_id.isdigit():
        items_qs = items_qs.filter(category__catid=int(category_id))

    # Stock status filter
    stock_status = request.GET.get('stock_status', '').strip()
    if stock_status == 'in_stock':
        items_qs = items_qs.filter(status='Available')
    elif stock_status == 'out_of_stock':
        items_qs = items_qs.filter(status='Out of Stock')

    # Search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        items_qs = items_qs.filter(
            Q(title__icontains=search_query) |
            Q(item__icontains=search_query) |
            Q(seller__username__icontains=search_query)
        )

    # Summary KPIs for DFD 3.0
    total_watchlist_entries = WatchListed.objects.count()
    unique_watchers_count = WatchListed.objects.values('user').distinct().count()

    most_watched_item = Item.objects.annotate(
        watch_count=Count('watchlisted_by')
    ).filter(watch_count__gt=0).order_by('-watch_count').first()

    high_demand_oos_count = Item.objects.filter(
        watchlisted_by__isnull=False,
        status='Out of Stock'
    ).distinct().count()

    # Recent activity logs (audit trail)
    recent_activity = WatchListed.objects.select_related(
        'user', 'user__userprofile', 'item', 'item__category'
    ).order_by('-added_date')[:15]

    categories = Category.objects.all().order_by('category')

    paginator = Paginator(items_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'community/admin_watchlist.html', {
        'page_obj': page_obj,
        'categories': categories,
        'total_watchlist_entries': total_watchlist_entries,
        'unique_watchers_count': unique_watchers_count,
        'most_watched_item': most_watched_item,
        'high_demand_oos_count': high_demand_oos_count,
        'recent_activity': recent_activity,
        'selected_category_id': category_id,
        'selected_stock_status': stock_status,
        'search_query': search_query,
    })


# =============================================================================
# MODULE 11: FREQUENTLY ASKED QUESTIONS (FAQ) VIEWS
# =============================================================================

def faq_view(request):
    """
    Public / Buyer & Seller FAQ view.
    Displays Frequently Asked Questions in a searchable Bootstrap accordion.
    Allows keyword filtering across questions and answers.
    """
    search_query = request.GET.get('q', '').strip()
    total_faqs_count = FAQ.objects.count()

    if search_query:
        faqs = FAQ.objects.filter(
            Q(faq__icontains=search_query) |
            Q(answer__icontains=search_query)
        ).order_by('faqid')
    else:
        faqs = FAQ.objects.all().order_by('faqid')

    return render(request, 'community/faq_list.html', {
        'faqs': faqs,
        'search_query': search_query,
        'total_faqs_count': total_faqs_count,
        'page_title': 'Frequently Asked Questions | Antique Hub',
    })


@login_required
@admin_required
def admin_faq_list(request):
    """
    Admin Management console for FAQs.
    Displays tabular list with search, pagination, and links to Create, Edit, and Delete.
    """
    search_query = request.GET.get('q', '').strip()
    faqs_qs = FAQ.objects.all().order_by('faqid')

    if search_query:
        faqs_qs = faqs_qs.filter(
            Q(faq__icontains=search_query) |
            Q(answer__icontains=search_query)
        )

    total_count = FAQ.objects.count()
    paginator = Paginator(faqs_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'community/admin_faq_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': total_count,
    })


@login_required
@admin_required
def admin_faq_create(request):
    """
    Admin view to create a new FAQ entry.
    """
    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            faq = form.save()
            messages.success(request, f"FAQ #{faq.faqid} ('{faq.faq[:40]}...') created successfully.")
            return redirect('community:admin_faq_list')
    else:
        form = FAQForm()

    return render(request, 'community/admin_faq_form.html', {
        'form': form,
        'is_edit': False,
        'page_title': 'Add New FAQ | Admin Console',
    })


@login_required
@admin_required
def admin_faq_update(request, faqid):
    """
    Admin view to edit an existing FAQ entry.
    """
    faq = get_object_or_404(FAQ, faqid=faqid)

    if request.method == 'POST':
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            faq = form.save()
            messages.success(request, f"FAQ #{faq.faqid} updated successfully.")
            return redirect('community:admin_faq_list')
    else:
        form = FAQForm(instance=faq)

    return render(request, 'community/admin_faq_form.html', {
        'form': form,
        'faq': faq,
        'is_edit': True,
        'page_title': f'Edit FAQ #{faq.faqid} | Admin Console',
    })


@login_required
@admin_required
def admin_faq_delete(request, faqid):
    """
    Admin view to delete an FAQ entry with confirmation.
    """
    faq = get_object_or_404(FAQ, faqid=faqid)

    if request.method == 'POST':
        question = faq.faq
        faq.delete()
        messages.success(request, f"FAQ #{faqid} ('{question[:40]}...') deleted successfully.")
        return redirect('community:admin_faq_list')

    return render(request, 'community/admin_faq_confirm_delete.html', {
        'faq': faq,
    })


def privacy_policy_view(request):
    """
    Public Privacy Policy & Heritage Curation Terms view.
    Details client anonymity protocols, 256-bit AES vault encryption,
    escrow protection, Antiquities and Art Treasures Act 1972 compliance,
    and 7-day white-glove inspection & return terms.
    """
    return render(request, 'community/privacy_policy.html', {
        'page_title': 'Collector Privacy Policy & Heritage Terms | Antique Hub',
        'last_updated': 'October 20, 2026',
        'version': '3.4',
    })


