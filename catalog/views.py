"""
Catalog Views for Antique Hub (Module 3).
Handles:
- Admin-only CRUD for Antique Categories (with item count and deletion protection)
- Admin-only CRUD for Antique SubCategories (with item count and deletion protection)
- AJAX endpoint for cascading subcategories (reused in seller upload & buyer search)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Avg
from django.http import JsonResponse

from accounts.decorators import admin_required, seller_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Category, SubCategory, Item
from .forms import CategoryForm, SubCategoryForm, ItemUploadForm, ItemEditForm
from inventory.models import Stock


# ======================================================================
# 1. Category Admin CRUD
# ======================================================================

@admin_required
def category_list(request):
    """
    Admin view listing all antique categories with item counts, search, and pagination.
    """
    query = request.GET.get('q', '').strip()

    categories_qs = Category.objects.annotate(
        items_count=Count('items', distinct=True),
        subcategories_count=Count('subcategories', distinct=True)
    ).order_by('category')

    if query:
        categories_qs = categories_qs.filter(
            Q(category__icontains=query) | Q(description__icontains=query)
        )

    paginator = Paginator(categories_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/category_list.html', {
        'page_obj': page_obj,
        'query': query,
        'page_title': 'Antique Categories | Admin Console',
    })


@admin_required
def category_add(request):
    """
    Add a new Antique Category.
    """
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.category}' added successfully.")
            return redirect('catalog:category_list')
        else:
            messages.error(request, "Failed to create category. Please correct the error below.")
    else:
        form = CategoryForm()

    return render(request, 'catalog/category_form.html', {
        'form': form,
        'action_title': 'Add New Antique Category',
        'page_title': 'Add Category | Admin',
    })


@admin_required
def category_edit(request, cat_id):
    """
    Edit an existing Antique Category.
    """
    cat = get_object_or_404(Category, catid=cat_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.category}' updated successfully.")
            return redirect('catalog:category_list')
        else:
            messages.error(request, "Failed to update category. Please correct the error below.")
    else:
        form = CategoryForm(instance=cat)

    return render(request, 'catalog/category_form.html', {
        'form': form,
        'category_obj': cat,
        'action_title': f"Edit Category: {cat.category}",
        'page_title': f"Edit Category: {cat.category} | Admin",
    })


@admin_required
def category_delete(request, cat_id):
    """
    Delete confirmation and action for Category.
    BLOCKS deletion if the category has items or subcategories!
    """
    cat = get_object_or_404(Category, catid=cat_id)
    items_count = cat.items.count()
    subcategories_count = cat.subcategories.count()

    if request.method == 'POST':
        # Relational Protection: Block deletion if items exist
        if items_count > 0:
            messages.error(
                request,
                f"Cannot delete Category '{cat.category}' because it contains {items_count} "
                "antique item(s). Please delete or reassign all items first."
            )
            return redirect('catalog:category_list')

        # Relational Protection: Block deletion if subcategories exist
        if subcategories_count > 0:
            messages.error(
                request,
                f"Cannot delete Category '{cat.category}' because it has {subcategories_count} "
                "associated subcategory(s). Please delete or reassign all subcategories first."
            )
            return redirect('catalog:category_list')

        cat_name = cat.category
        cat.delete()
        messages.success(request, f"Category '{cat_name}' deleted successfully.")
        return redirect('catalog:category_list')

    return render(request, 'catalog/category_confirm_delete.html', {
        'category': cat,
        'items_count': items_count,
        'subcategories_count': subcategories_count,
        'page_title': f"Confirm Deletion: {cat.category} | Admin",
    })


# ======================================================================
# 2. SubCategory Admin CRUD
# ======================================================================

@admin_required
def subcategory_list(request):
    """
    Admin view listing all subcategories with category filter, search, item counts, and pagination.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category_id', '').strip()

    subcats_qs = SubCategory.objects.select_related('category').annotate(
        items_count=Count('items', distinct=True)
    ).order_by('category__category', 'subcategory')

    if category_id:
        subcats_qs = subcats_qs.filter(category_id=category_id)

    if query:
        subcats_qs = subcats_qs.filter(
            Q(subcategory__icontains=query) | Q(category__category__icontains=query)
        )

    categories = Category.objects.all().order_by('category')
    paginator = Paginator(subcats_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/subcategory_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category_id': category_id,
        'query': query,
        'page_title': 'Antique SubCategories | Admin Console',
    })


@admin_required
def subcategory_add(request):
    """
    Add a new SubCategory (needs a parent Category).
    """
    initial = {}
    category_id = request.GET.get('category_id')
    if category_id:
        initial['category'] = category_id

    if request.method == 'POST':
        form = SubCategoryForm(request.POST)
        if form.is_valid():
            subcat = form.save()
            messages.success(
                request,
                f"SubCategory '{subcat.subcategory}' added successfully under '{subcat.category.category}'."
            )
            return redirect('catalog:subcategory_list')
        else:
            messages.error(request, "Failed to add subcategory. Please check the errors below.")
    else:
        form = SubCategoryForm(initial=initial)

    return render(request, 'catalog/subcategory_form.html', {
        'form': form,
        'action_title': 'Add New SubCategory',
        'page_title': 'Add SubCategory | Admin',
    })


@admin_required
def subcategory_edit(request, subcat_id):
    """
    Edit an existing SubCategory.
    """
    subcat = get_object_or_404(SubCategory, subcatid=subcat_id)

    if request.method == 'POST':
        form = SubCategoryForm(request.POST, instance=subcat)
        if form.is_valid():
            subcat = form.save()
            messages.success(request, f"SubCategory '{subcat.subcategory}' updated successfully.")
            return redirect('catalog:subcategory_list')
        else:
            messages.error(request, "Failed to update subcategory. Please check the errors below.")
    else:
        form = SubCategoryForm(instance=subcat)

    return render(request, 'catalog/subcategory_form.html', {
        'form': form,
        'subcategory_obj': subcat,
        'action_title': f"Edit SubCategory: {subcat.subcategory}",
        'page_title': f"Edit SubCategory: {subcat.subcategory} | Admin",
    })


@admin_required
def subcategory_delete(request, subcat_id):
    """
    Delete confirmation and action for SubCategory.
    BLOCKS deletion if the subcategory has items!
    """
    subcat = get_object_or_404(SubCategory, subcatid=subcat_id)
    items_count = subcat.items.count()

    if request.method == 'POST':
        # Relational Protection: Block deletion if items exist
        if items_count > 0:
            messages.error(
                request,
                f"Cannot delete SubCategory '{subcat.subcategory}' because it contains {items_count} "
                "antique item(s). Please delete or reassign all items first."
            )
            return redirect('catalog:subcategory_list')

        subcat_name = subcat.subcategory
        subcat.delete()
        messages.success(request, f"SubCategory '{subcat_name}' deleted successfully.")
        return redirect('catalog:subcategory_list')

    return render(request, 'catalog/subcategory_confirm_delete.html', {
        'subcategory': subcat,
        'items_count': items_count,
        'page_title': f"Confirm Deletion: {subcat.subcategory} | Admin",
    })


# ======================================================================
# 3. JSON AJAX Endpoint (SubCategories by Category)
# ======================================================================

def load_subcategories_ajax(request):
    """
    AJAX JSON endpoint to return subcategories for a selected category.
    Reused across:
    1. Seller item upload form (cascading category -> subcategory)
    2. Buyer marketplace filter bar
    GET /catalog/ajax/load-subcategories/?category_id=<id>
    """
    category_id = request.GET.get('category_id')
    if not category_id:
        return JsonResponse({'subcategories': []})

    subcategories = SubCategory.objects.filter(category_id=category_id).order_by('subcategory').values(
        'subcatid', 'subcategory'
    )
    return JsonResponse({'subcategories': list(subcategories)})


# ======================================================================
# 4. Seller Items Management (Module 4)
# ======================================================================

@seller_required
def seller_item_list(request):
    """
    Activated Seller view listing "My Items" with status badges, stock count, and action controls.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    items_qs = Item.objects.filter(seller=request.user).select_related(
        'category', 'subcategory'
    ).prefetch_related('stock_records').order_by('-post_date')

    if status_filter:
        items_qs = items_qs.filter(status=status_filter)

    if query:
        items_qs = items_qs.filter(
            Q(title__icontains=query) |
            Q(item__icontains=query) |
            Q(origin__icontains=query) |
            Q(category__category__icontains=query)
        )

    paginator = Paginator(items_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/seller_item_list.html', {
        'page_obj': page_obj,
        'query': query,
        'selected_status': status_filter,
        'page_title': 'My Antique Listings | Seller Hub',
    })


@seller_required
def item_create(request):
    """
    Activated Seller upload view for new antique items.
    Dual Creation (DFD 2.1 & 2.2):
    Saves Item and immediately creates its matching Stock row in inventory.
    """
    if request.method == 'POST':
        form = ItemUploadForm(request.POST, request.FILES)
        if form.is_valid():
            opening_stock = form.cleaned_data.get('opening_stock', 1)
            item = form.save(seller_user=request.user)
            messages.success(
                request,
                f"Antique listing '{item.title}' (SKU: {item.item}) uploaded successfully with {opening_stock} unit(s) in stock."
            )
            return redirect('catalog:seller_items')
        else:
            messages.error(request, "Failed to upload item. Please check the highlighted errors below.")
    else:
        form = ItemUploadForm()

    categories = Category.objects.all().order_by('category')

    return render(request, 'catalog/item_form.html', {
        'form': form,
        'categories': categories,
        'action_title': 'Upload New Antique Artifact',
        'is_create': True,
        'page_title': 'Upload Antique Item | Seller Hub',
    })


@login_required
def item_update(request, item_id):
    """
    Edit view for an antique listing.
    Ownership check: Sellers can only edit their own items. Admins can edit any item.
    """
    item = get_object_or_404(Item, itemid=item_id)

    # Permission check: seller can only edit own item, admin can edit any
    is_admin = request.user.is_superuser or request.user.is_staff
    if not is_admin and item.seller != request.user:
        raise PermissionDenied("You do not have permission to edit this antique listing.")

    if request.method == 'POST':
        form = ItemEditForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"Antique listing '{item.title}' updated successfully.")
            if is_admin and not (item.seller == request.user):
                return redirect('catalog:admin_items')
            return redirect('catalog:seller_items')
        else:
            messages.error(request, "Failed to update item. Please check the highlighted errors below.")
    else:
        form = ItemEditForm(instance=item)

    categories = Category.objects.all().order_by('category')

    return render(request, 'catalog/item_form.html', {
        'form': form,
        'item_obj': item,
        'categories': categories,
        'action_title': f"Edit Listing: {item.title}",
        'is_create': False,
        'page_title': f"Edit {item.title} | Antique Hub",
    })


@login_required
def item_delete(request, item_id):
    """
    Delete confirmation and action for an antique listing.
    Ownership check: Sellers can only delete their own items. Admins can delete any item.
    """
    item = get_object_or_404(Item, itemid=item_id)
    is_admin = request.user.is_superuser or request.user.is_staff

    if not is_admin and item.seller != request.user:
        raise PermissionDenied("You do not have permission to delete this antique listing.")

    if request.method == 'POST':
        item_title = item.title
        item.delete()
        messages.success(request, f"Antique listing '{item_title}' deleted successfully.")
        if is_admin and not (item.seller == request.user):
            return redirect('catalog:admin_items')
        return redirect('catalog:seller_items')

    return render(request, 'catalog/item_confirm_delete.html', {
        'item': item,
        'page_title': f"Confirm Deletion: {item.title} | Antique Hub",
    })


# ======================================================================
# 5. Admin Manage Items & Visibility
# ======================================================================

@admin_required
def admin_item_list(request):
    """
    Admin master catalog management table ("Manage Items").
    Allows Administrators to view, edit, hide/unhide, or delete any listing across all sellers.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_id = request.GET.get('category_id', '').strip()

    items_qs = Item.objects.select_related(
        'category', 'subcategory', 'seller', 'seller__userprofile'
    ).prefetch_related('stock_records').order_by('-post_date')

    if status_filter:
        items_qs = items_qs.filter(status=status_filter)

    if category_id:
        items_qs = items_qs.filter(category_id=category_id)

    if query:
        items_qs = items_qs.filter(
            Q(title__icontains=query) |
            Q(item__icontains=query) |
            Q(seller__username__icontains=query) |
            Q(seller__userprofile__contactname__icontains=query) |
            Q(origin__icontains=query)
        )

    categories = Category.objects.all().order_by('category')
    paginator = Paginator(items_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/admin_item_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category_id': category_id,
        'selected_status': status_filter,
        'query': query,
        'page_title': 'Manage All Items | Admin Console',
    })


@admin_required
def admin_toggle_item_status(request, item_id):
    """
    Admin action to quickly toggle item visibility between 'Hidden' and 'Available'.
    POST /catalog/admin/items/<item_id>/toggle-status/
    """
    item = get_object_or_404(Item, itemid=item_id)
    if item.status == 'Hidden':
        item.status = 'Available' if item.current_stock > 0 else 'Out of Stock'
    else:
        item.status = 'Hidden'
    item.save()

    messages.success(request, f"Item '{item.title}' visibility status updated to '{item.status}'.")
    return redirect('catalog:admin_items')


# ======================================================================
# 6. Buyer Marketplace Catalogue & Search (Module 6)
# ======================================================================

def item_list(request):
    """
    Public Buyer Catalogue / Marketplace view (Module 6).
    Features:
    - Category-wise browsing and SubCategory filtering
    - Keyword search across SKU, Title, Origin, and Description
    - Price range (min_price, max_price)
    - Age filter (min_age, max_age)
    - Sorting:
        * 'newest' (Listing date desc - default)
        * 'price_asc' (Price: Low to High)
        * 'price_desc' (Price: High to Low)
        * 'oldest' (Era age desc)
        * 'discounted' (Only items with active category discounts)
    - Pagination (9 items per page)
    - Query optimization with select_related & prefetch_related
    - Badges for Discounts, Live Stock, and Location
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category_id', '').strip()
    subcategory_id = request.GET.get('subcategory_id', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    min_age = request.GET.get('min_age', '').strip()
    max_age = request.GET.get('max_age', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    # Base Query: Public artifacts (Available and Out of Stock, Hidden excluded)
    items_qs = Item.objects.filter(status__in=['Available', 'Out of Stock']).select_related(
        'category',
        'subcategory',
        'seller',
        'seller__userprofile',
        'seller__userprofile__location',
        'seller__userprofile__district',
        'seller__userprofile__state',
    ).prefetch_related(
        'stock_records',
        'category__discounts',
    )

    # 1. Keyword search (item SKU, title, origin, description)
    if query:
        items_qs = items_qs.filter(
            Q(item__icontains=query) |
            Q(title__icontains=query) |
            Q(origin__icontains=query) |
            Q(description__icontains=query)
        )

    # 2. Category Filter
    if category_id:
        items_qs = items_qs.filter(category_id=category_id)

    # 3. SubCategory Filter
    if subcategory_id:
        items_qs = items_qs.filter(subcategory_id=subcategory_id)

    # 4. Price Range Filter
    if min_price:
        try:
            items_qs = items_qs.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            items_qs = items_qs.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # 5. Age Range Filter
    if min_age:
        try:
            items_qs = items_qs.filter(years_old__gte=int(min_age))
        except ValueError:
            pass

    if max_age:
        try:
            items_qs = items_qs.filter(years_old__lte=int(max_age))
        except ValueError:
            pass

    # 6. Sorting
    if sort_by == 'price_asc':
        items_qs = items_qs.order_by('price')
    elif sort_by == 'price_desc':
        items_qs = items_qs.order_by('-price')
    elif sort_by == 'oldest':
        items_qs = items_qs.order_by('-years_old')
    elif sort_by == 'discounted':
        today = timezone.localdate()
        items_qs = items_qs.filter(
            category__discounts__startdate__lte=today,
            category__discounts__enddate__gte=today
        ).distinct().order_by('-post_date')
    else:  # 'newest' default
        items_qs = items_qs.order_by('-post_date')

    # Categories for filter sidebar with count
    categories = Category.objects.annotate(
        active_item_count=Count('items', filter=Q(items__status__in=['Available', 'Out of Stock']))
    ).order_by('category')

    # Subcategories based on chosen category or all
    if category_id:
        subcategories = SubCategory.objects.filter(category_id=category_id).order_by('subcategory')
    else:
        subcategories = SubCategory.objects.all().order_by('category__category', 'subcategory')

    # Active filters counter
    active_filters_count = sum(bool(x) for x in [
        query, category_id, subcategory_id, min_price, max_price, min_age, max_age
    ])

    paginator = Paginator(items_qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/item_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'subcategories': subcategories,
        'selected_category_id': category_id,
        'selected_subcategory_id': subcategory_id,
        'selected_sort': sort_by,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'min_age': min_age,
        'max_age': max_age,
        'active_filters_count': active_filters_count,
        'page_title': 'Heritage Marketplace & Antique Catalogue | Antique Hub',
    })


# ======================================================================
# 7. Item Detail Page (Public & Authenticated)
# ======================================================================

def item_detail(request, item_id):
    """
    Comprehensive public item detail page.
    Displays:
    - Dual photographs with interactive gallery view
    - History, era provenance, and years old
    - Price, active discount badge & discounted price calculation
    - Live stock availability badge
    - Seller name, contact name, and geographical location (Ward, District, State)
    - Full condition and provenance description
    - Verified comments and reviews list
    - Add to Cart and Add to Watchlist actions
    """
    item = get_object_or_404(
        Item.objects.select_related(
            'category',
            'subcategory',
            'seller',
            'seller__userprofile',
            'seller__userprofile__location',
            'seller__userprofile__district',
            'seller__userprofile__state'
        ).prefetch_related(
            'stock_records',
            'category__discounts',
            'item_comments__buyer',
            'item_comments__buyer__userprofile'
        ),
        itemid=item_id
    )

    # If hidden, only admin or the item's seller can view
    if item.status == 'Hidden':
        is_admin = request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)
        is_owner = request.user.is_authenticated and item.seller == request.user
        if not (is_admin or is_owner):
            messages.warning(request, "This antique listing is currently hidden from the marketplace.")
            return redirect('accounts:home')

    # Verified reviews and comments
    comments = item.item_comments.select_related('buyer', 'buyer__userprofile').order_by('-cdate')
    rated_comments = comments.filter(rating__isnull=False)
    rated_count = rated_comments.count()
    avg_rating = rated_comments.aggregate(avg=Avg('rating'))['avg']
    average_rating = round(avg_rating, 1) if avg_rating else None

    # Watchlist status & purchase verification for authenticated user
    is_watchlisted = False
    has_purchased = False
    if request.user.is_authenticated:
        is_watchlisted = item.watchlisted_by.filter(user=request.user).exists()
        from community.utils import has_user_purchased_item
        has_purchased = has_user_purchased_item(request.user, item)

    return render(request, 'catalog/item_detail.html', {
        'item': item,
        'comments': comments,
        'is_watchlisted': is_watchlisted,
        'has_purchased': has_purchased,
        'average_rating': average_rating,
        'rated_count': rated_count,
        'page_title': f"{item.title} | Antique Hub",
    })


