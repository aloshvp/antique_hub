"""
Views for Inventory Stock Management (Module 5).
Includes:
- Seller "View Stock" with low-stock warnings (threshold 2) & Restock action
- Admin "Stock Management" master table with filters, low-stock metrics & Restock action
- Add Stock (Restock) handler for increasing arrived & current stock
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.contrib.auth.models import User

from accounts.decorators import seller_required, admin_required
from catalog.models import Category, Item
from .models import Stock, Discount
from .forms import AddStockForm, DiscountForm
from .utils import get_effective_price


# ======================================================================
# 1. Seller "View Stock" Dashboard
# ======================================================================

@seller_required
def seller_stock_list(request):
    """
    Activated Seller inventory stock dashboard.
    Lists only items belonging to the authenticated seller.
    Highlights low stock warnings (threshold <= 2) and out-of-stock items.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # Base queryset: only items owned by this seller
    stocks_qs = Stock.objects.filter(item__seller=request.user).select_related(
        'item', 'item__category', 'item__subcategory'
    ).order_by('-stockdate')

    # Summary metric statistics
    total_items = stocks_qs.count()
    total_units_available = stocks_qs.aggregate(total=Sum('cur_stock'))['total'] or 0
    total_arrived_units = stocks_qs.aggregate(total=Sum('tot_arr_stock'))['total'] or 0
    low_stock_count = stocks_qs.filter(cur_stock__gt=0, cur_stock__lte=Stock.LOW_STOCK_THRESHOLD).count()
    out_of_stock_count = stocks_qs.filter(cur_stock=0).count()

    # Search filter
    if query:
        stocks_qs = stocks_qs.filter(
            Q(item__title__icontains=query) |
            Q(item__item__icontains=query) |
            Q(item__origin__icontains=query) |
            Q(item__category__category__icontains=query)
        )

    # Status filter
    if status_filter == 'low_stock':
        stocks_qs = stocks_qs.filter(cur_stock__gt=0, cur_stock__lte=Stock.LOW_STOCK_THRESHOLD)
    elif status_filter == 'out_of_stock':
        stocks_qs = stocks_qs.filter(cur_stock=0)
    elif status_filter == 'in_stock':
        stocks_qs = stocks_qs.filter(cur_stock__gt=Stock.LOW_STOCK_THRESHOLD)

    # Pagination (10 records per page)
    paginator = Paginator(stocks_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/seller_stock_list.html', {
        'page_obj': page_obj,
        'query': query,
        'selected_status': status_filter,
        'total_items': total_items,
        'total_units_available': total_units_available,
        'total_arrived_units': total_arrived_units,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'page_title': 'Inventory Stock Ledger | Seller Hub',
    })


@seller_required
def seller_add_stock(request, stock_id):
    """
    Restock view for an activated seller.
    Increases total arrived stock and current stock, and updates stockdate.
    Ownership protection: Sellers can only add stock to their own items.
    """
    stock = get_object_or_404(
        Stock.objects.select_related('item', 'item__category', 'item__subcategory'),
        stockid=stock_id
    )

    # Relational ownership check
    if stock.item.seller != request.user:
        raise PermissionDenied("You do not have permission to restock this antique listing.")

    if request.method == 'POST':
        form = AddStockForm(request.POST)
        if form.is_valid():
            quantity_to_add = form.cleaned_data['quantity_to_add']
            stock.add_stock(quantity_to_add)
            messages.success(
                request,
                f"Successfully restocked {quantity_to_add} unit(s) for '{stock.item.title}'. "
                f"Total Available: {stock.cur_stock} units."
            )
            return redirect('inventory:seller_stock')
        else:
            messages.error(request, "Failed to restock item. Please check the quantity entered.")
    else:
        form = AddStockForm()

    return render(request, 'inventory/add_stock_form.html', {
        'form': form,
        'stock': stock,
        'is_admin': False,
        'action_title': f"Restock: {stock.item.title}",
        'page_title': f"Restock {stock.item.title} | Seller Hub",
    })


# ======================================================================
# 2. Admin "Stock Management" Master Console
# ======================================================================

@admin_required
def admin_stock_list(request):
    """
    Admin master stock management console.
    Supervises stock across all registered sellers and items.
    Allows filtering by seller, category, status, and restocking any artifact.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    seller_id = request.GET.get('seller_id', '').strip()
    category_id = request.GET.get('category_id', '').strip()

    # Base master queryset
    stocks_qs = Stock.objects.select_related(
        'item',
        'item__seller',
        'item__seller__userprofile',
        'item__category',
        'item__subcategory'
    ).order_by('-stockdate')

    # Summary metrics across entire catalog
    total_tracked_items = stocks_qs.count()
    total_units_available = stocks_qs.aggregate(total=Sum('cur_stock'))['total'] or 0
    total_arrived_units = stocks_qs.aggregate(total=Sum('tot_arr_stock'))['total'] or 0
    low_stock_count = stocks_qs.filter(cur_stock__gt=0, cur_stock__lte=Stock.LOW_STOCK_THRESHOLD).count()
    out_of_stock_count = stocks_qs.filter(cur_stock=0).count()

    # Filter by Seller
    if seller_id:
        stocks_qs = stocks_qs.filter(item__seller_id=seller_id)

    # Filter by Category
    if category_id:
        stocks_qs = stocks_qs.filter(item__category_id=category_id)

    # Status filter
    if status_filter == 'low_stock':
        stocks_qs = stocks_qs.filter(cur_stock__gt=0, cur_stock__lte=Stock.LOW_STOCK_THRESHOLD)
    elif status_filter == 'out_of_stock':
        stocks_qs = stocks_qs.filter(cur_stock=0)
    elif status_filter == 'in_stock':
        stocks_qs = stocks_qs.filter(cur_stock__gt=Stock.LOW_STOCK_THRESHOLD)

    # Search filter
    if query:
        stocks_qs = stocks_qs.filter(
            Q(item__title__icontains=query) |
            Q(item__item__icontains=query) |
            Q(item__seller__username__icontains=query) |
            Q(item__seller__userprofile__contactname__icontains=query) |
            Q(item__category__category__icontains=query)
        )

    # Sellers and Categories for dropdown filters
    sellers = User.objects.filter(antique_items__isnull=False).distinct().order_by('username')
    categories = Category.objects.all().order_by('category')

    # Pagination
    paginator = Paginator(stocks_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/admin_stock_list.html', {
        'page_obj': page_obj,
        'sellers': sellers,
        'categories': categories,
        'selected_seller_id': seller_id,
        'selected_category_id': category_id,
        'selected_status': status_filter,
        'query': query,
        'total_tracked_items': total_tracked_items,
        'total_units_available': total_units_available,
        'total_arrived_units': total_arrived_units,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'page_title': 'Stock Management Console | Admin',
    })


@admin_required
def admin_add_stock(request, stock_id):
    """
    Admin restock view for any antique listing.
    """
    stock = get_object_or_404(
        Stock.objects.select_related('item', 'item__seller', 'item__category'),
        stockid=stock_id
    )

    if request.method == 'POST':
        form = AddStockForm(request.POST)
        if form.is_valid():
            quantity_to_add = form.cleaned_data['quantity_to_add']
            stock.add_stock(quantity_to_add)
            messages.success(
                request,
                f"Admin restocked {quantity_to_add} unit(s) for '{stock.item.title}'. "
                f"New Available Stock: {stock.cur_stock} units."
            )
            return redirect('inventory:admin_stock')
        else:
            messages.error(request, "Failed to restock item. Please check the quantity entered.")
    else:
        form = AddStockForm()

    return render(request, 'inventory/add_stock_form.html', {
        'form': form,
        'stock': stock,
        'is_admin': True,
        'action_title': f"Admin Restock: {stock.item.title}",
        'page_title': f"Restock {stock.item.title} | Admin",
    })


# ======================================================================
# 4. Module 12: Promotional Discounts Management (Admin CRUD)
# ======================================================================

@admin_required
def admin_discount_list(request):
    """
    Admin Promotional Discounts Master Dashboard.
    Provides:
    - Tabular listing of all discount campaigns with category and percentage
    - Status filtering: All, Active (live now), Upcoming, Expired
    - Category filtering & search
    - Summary KPI cards (Active Campaigns, Upcoming, Expired, Avg Discount %)
    - Action buttons for Add Discount, Edit, and Delete
    """
    today = timezone.localdate()
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_id = request.GET.get('category_id', '').strip()

    discounts_qs = Discount.objects.select_related('applicable_cat').order_by('-startdate', '-discountid')

    # Summary KPI Statistics
    total_discounts_count = discounts_qs.count()
    active_count = discounts_qs.filter(startdate__lte=today, enddate__gte=today).count()
    upcoming_count = discounts_qs.filter(startdate__gt=today).count()
    expired_count = discounts_qs.filter(enddate__lt=today).count()
    avg_discount = discounts_qs.filter(startdate__lte=today, enddate__gte=today).aggregate(
        avg=Avg('discount_percent')
    )['avg'] or 0.0

    # Search query across category name or discount percent
    if query:
        discounts_qs = discounts_qs.filter(
            Q(applicable_cat__category__icontains=query) |
            Q(discount_percent__icontains=query)
        )

    # Category filter
    if category_id:
        if category_id == 'all_storewide':
            discounts_qs = discounts_qs.filter(applicable_cat__isnull=True)
        elif category_id.isdigit():
            discounts_qs = discounts_qs.filter(applicable_cat_id=int(category_id))

    # Status filter
    if status_filter == 'active':
        discounts_qs = discounts_qs.filter(startdate__lte=today, enddate__gte=today)
    elif status_filter == 'upcoming':
        discounts_qs = discounts_qs.filter(startdate__gt=today)
    elif status_filter == 'expired':
        discounts_qs = discounts_qs.filter(enddate__lt=today)

    categories = Category.objects.all().order_by('category')
    paginator = Paginator(discounts_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/admin_discount_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'total_discounts_count': total_discounts_count,
        'active_count': active_count,
        'upcoming_count': upcoming_count,
        'expired_count': expired_count,
        'avg_discount': round(avg_discount, 1),
        'search_query': query,
        'status_filter': status_filter,
        'selected_category_id': category_id,
        'today': today,
        'page_title': 'Promotional Discounts Management | Admin Console',
    })


@admin_required
def admin_discount_create(request):
    """
    Admin "Add Discount of Items" view.
    Choose an applicable category (or all for storewide discount),
    discount percent (1% to 90%), start date, and end date with validation
    that end date is strictly after start date.
    """
    if request.method == 'POST':
        form = DiscountForm(request.POST)
        if form.is_valid():
            discount = form.save()
            target = discount.applicable_cat.category if discount.applicable_cat else "All Categories"
            messages.success(
                request,
                f"Promotional discount of {discount.discount_percent}% on '{target}' "
                f"({discount.startdate} to {discount.enddate}) created successfully!"
            )
            return redirect('inventory:admin_discounts')
        else:
            messages.error(request, "Failed to create discount campaign. Please resolve the validation errors below.")
    else:
        # Prepopulate default dates: today to +30 days
        today = timezone.localdate()
        end = today + timezone.timedelta(days=30)
        form = DiscountForm(initial={
            'startdate': today,
            'enddate': end,
            'discount_percent': 15.00,
        })

    return render(request, 'inventory/admin_discount_form.html', {
        'form': form,
        'is_edit': False,
        'page_title': 'Add Discount of Items | Admin Console',
    })


@admin_required
def admin_discount_update(request, discount_id):
    """
    Admin view to edit an existing discount campaign.
    """
    discount = get_object_or_404(Discount, discountid=discount_id)

    if request.method == 'POST':
        form = DiscountForm(request.POST, instance=discount)
        if form.is_valid():
            discount = form.save()
            target = discount.applicable_cat.category if discount.applicable_cat else "All Categories"
            messages.success(
                request,
                f"Discount #{discount.discountid} ({discount.discount_percent}% on {target}) updated successfully!"
            )
            return redirect('inventory:admin_discounts')
        else:
            messages.error(request, "Failed to update discount. Please review the errors below.")
    else:
        form = DiscountForm(instance=discount)

    return render(request, 'inventory/admin_discount_form.html', {
        'form': form,
        'discount': discount,
        'is_edit': True,
        'page_title': f'Edit Discount #{discount.discountid} | Admin Console',
    })


@admin_required
def admin_discount_delete(request, discount_id):
    """
    Admin view to delete a promotional discount campaign with confirmation.
    """
    discount = get_object_or_404(Discount.objects.select_related('applicable_cat'), discountid=discount_id)

    if request.method == 'POST':
        cat_name = discount.applicable_cat.category if discount.applicable_cat else "All Categories"
        percent = discount.discount_percent
        discount.delete()
        messages.success(
            request,
            f"Discount campaign ({percent}% on {cat_name}) has been deleted successfully."
        )
        return redirect('inventory:admin_discounts')

    return render(request, 'inventory/admin_discount_confirm_delete.html', {
        'discount': discount,
        'page_title': f'Delete Discount #{discount.discountid} | Admin',
    })


# ======================================================================
# 5. Buyer "Search item Discount" Page (Module 12)
# ======================================================================

def buyer_discount_search(request):
    """
    Buyer "Search item Discount" showcase page.
    Lists currently discounted items where:
    - Discount is active (startdate <= today <= enddate)
    - Effective discounted price is calculated via get_effective_price()
    - Expired discounts automatically stop applying
    Supports keyword search, category filter, price range, age filter, and sorting.
    """
    today = timezone.localdate()

    # Determine which categories have currently active discounts
    active_discounts = Discount.objects.filter(
        startdate__lte=today,
        enddate__gte=today,
        discount_percent__gt=0
    ).select_related('applicable_cat')

    has_storewide_discount = active_discounts.filter(applicable_cat__isnull=True).exists()
    active_cat_ids = list(active_discounts.filter(applicable_cat__isnull=False).values_list('applicable_cat_id', flat=True))

    # Base queryset of available antique listings
    if has_storewide_discount:
        items_qs = Item.objects.filter(status='Available')
    elif active_cat_ids:
        items_qs = Item.objects.filter(status='Available', category_id__in=active_cat_ids)
    else:
        items_qs = Item.objects.none()

    items_qs = items_qs.select_related(
        'category', 'subcategory', 'seller', 'seller__userprofile',
        'seller__userprofile__district', 'seller__userprofile__state'
    ).prefetch_related(
        'stock_records', 'category__discounts'
    )

    # 1. Keyword search (title, SKU, origin, description)
    query = request.GET.get('q', '').strip()
    if query:
        items_qs = items_qs.filter(
            Q(title__icontains=query) |
            Q(item__icontains=query) |
            Q(origin__icontains=query) |
            Q(description__icontains=query) |
            Q(category__category__icontains=query)
        )

    # 2. Category filter
    category_id = request.GET.get('category_id', '').strip()
    if category_id and category_id.isdigit():
        items_qs = items_qs.filter(category_id=int(category_id))

    # 3. Price filter
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    if min_price and min_price.isdigit():
        items_qs = items_qs.filter(price__gte=float(min_price))
    if max_price and max_price.isdigit():
        items_qs = items_qs.filter(price__lte=float(max_price))

    # 4. Age filter
    min_age = request.GET.get('min_age', '').strip()
    max_age = request.GET.get('max_age', '').strip()
    if min_age and min_age.isdigit():
        items_qs = items_qs.filter(years_old__gte=int(min_age))
    if max_age and max_age.isdigit():
        items_qs = items_qs.filter(years_old__lte=int(max_age))

    # 5. Sorting
    sort = request.GET.get('sort', 'discount_desc').strip()
    if sort == 'price_low':
        items_qs = items_qs.order_by('price')
    elif sort == 'price_high':
        items_qs = items_qs.order_by('-price')
    elif sort == 'oldest':
        items_qs = items_qs.order_by('-years_old')
    elif sort == 'newest':
        items_qs = items_qs.order_by('-post_date')
    else:  # default: discount_desc or newest
        items_qs = items_qs.order_by('-post_date')

    # Convert to list and sort by calculated discount percent if requested
    items_list = list(items_qs)
    if sort == 'discount_desc':
        items_list.sort(key=lambda it: it.discount_percent, reverse=True)

    # KPI Metrics
    total_discounted_count = len(items_list)
    max_discount_val = max([it.discount_percent for it in items_list], default=0)
    active_campaigns_count = active_discounts.count()

    categories = Category.objects.all().order_by('category')
    paginator = Paginator(items_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/buyer_discount_search.html', {
        'page_obj': page_obj,
        'categories': categories,
        'active_discounts': active_discounts,
        'total_discounted_count': total_discounted_count,
        'max_discount_val': max_discount_val,
        'active_campaigns_count': active_campaigns_count,
        'query': query,
        'selected_category_id': category_id,
        'min_price': min_price,
        'max_price': max_price,
        'min_age': min_age,
        'max_age': max_age,
        'selected_sort': sort,
        'today': today,
        'page_title': 'Search Item Discounts | Curated Offers | Antique Hub',
    })

