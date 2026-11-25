"""
Dashboard views for Module 13 - Admin Dashboard & Analytics.
Includes:
- Admin Overview Dashboard with KPI cards, Chart.js analytics (Sales by Month & Items by Category)
- Pending Sellers table with inline Activate / Deactivate actions
- Comprehensive Sidebar containing all menu links from the synopsis structure
- Manage Users Console with Block / Unblock and Seller Activation
- 6 Reports with Date Filtering, CSV Export & Publication-Quality ReportLab PDF Export:
  1. Users Report
  2. Items Report
  3. Orders Report
  4. Sales Report
  5. Payments Report
  6. Stock Report
"""

import csv
import json
from decimal import Decimal
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.core.paginator import Paginator

from accounts.models import UserProfile, Role
from accounts.decorators import admin_required
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock, Discount
from orders.models import PurchaseMaster, Purchase
from payments.models import Payment
from community.models import Comment, FAQ, WatchListed
from .reports_pdf import build_report_pdf


# ======================================================================
# 1. Admin Dashboard Overview
# ======================================================================

@admin_required
def admin_dashboard(request):
    """
    Main Administration Dashboard Console (Module 13).
    - KPI Cards: Total Users, Total Sellers, Total Buyers, Total Items, Total Orders, Total Revenue
    - Pending Sellers list with direct Activate / Deactivate controls
    - Interactive Chart.js Visualizations:
        1. Sales by month (Revenue & Orders count)
        2. Items distribution by category
    - Navigation sidebar with all synopsis module routes
    """
    today = timezone.localdate()

    # 1. KPI Metrics
    total_users = User.objects.count()
    total_sellers = UserProfile.objects.filter(role__role__iexact='seller').count()
    total_buyers = UserProfile.objects.filter(role__role__iexact='buyer').count()
    total_items = Item.objects.count()
    total_orders = PurchaseMaster.objects.count()
    total_revenue = PurchaseMaster.objects.filter(
        pay_status__in=['Paid', 'Completed']
    ).aggregate(tot=Sum('tot_amt'))['tot'] or Decimal('0.00')

    # Secondary health indicators
    pending_sellers_count = UserProfile.objects.filter(role__role__iexact='seller', status='Pending').count()
    low_stock_count = Stock.objects.filter(cur_stock__gt=0, cur_stock__lte=Stock.LOW_STOCK_THRESHOLD).count()
    out_of_stock_count = Stock.objects.filter(cur_stock=0).count()
    active_discounts_count = Discount.objects.filter(startdate__lte=today, enddate__gte=today).count()
    total_comments_count = Comment.objects.count()

    # 2. Pending Sellers List (Inline Activation Queue)
    pending_sellers = UserProfile.objects.filter(
        role__role__iexact='seller',
        status='Pending'
    ).select_related('login', 'state', 'district', 'location').order_by('-userid')[:8]

    # 3. Recent Platform Orders
    recent_orders = PurchaseMaster.objects.select_related(
        'buyer'
    ).prefetch_related('order_items', 'order_items__item').order_by('-purdate')[:6]

    # 4. Chart 1: Sales by Month (Last 6 Months)
    months_labels = []
    revenue_data = []
    order_counts_data = []

    # Generate sequential chronological 6-month window ending with current month
    for i in range(5, -1, -1):
        # Calculate year and month for offset i
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        label_str = datetime(year, month, 1).strftime('%b %Y')
        months_labels.append(label_str)

        month_orders = PurchaseMaster.objects.filter(
            purdate__year=year,
            purdate__month=month
        )
        count = month_orders.count()
        rev = month_orders.filter(
            pay_status__in=['Paid', 'Completed']
        ).aggregate(tot=Sum('tot_amt'))['tot'] or Decimal('0.00')

        order_counts_data.append(count)
        revenue_data.append(float(rev))

    # 5. Chart 2: Items by Category
    categories_qs = Category.objects.annotate(
        item_count=Count('items')
    ).filter(item_count__gt=0).order_by('-item_count')[:7]

    cat_labels = [c.category for c in categories_qs]
    cat_counts = [c.item_count for c in categories_qs]

    # Other categories bucket if more than 7 exist
    other_count = Category.objects.annotate(
        item_count=Count('items')
    ).exclude(catid__in=[c.catid for c in categories_qs]).aggregate(tot=Sum('item_count'))['tot'] or 0

    if other_count > 0:
        cat_labels.append('Other Collections')
        cat_counts.append(other_count)

    context = {
        'page_title': 'Executive Administration Dashboard | Antique Hub',
        'active_menu': 'dashboard',
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_buyers': total_buyers,
        'total_items': total_items,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_sellers_count': pending_sellers_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'active_discounts_count': active_discounts_count,
        'total_comments_count': total_comments_count,
        'pending_sellers': pending_sellers,
        'recent_orders': recent_orders,
        # Chart serialized data
        'chart_months_json': json.dumps(months_labels),
        'chart_revenue_json': json.dumps(revenue_data),
        'chart_orders_json': json.dumps(order_counts_data),
        'chart_cat_labels_json': json.dumps(cat_labels),
        'chart_cat_counts_json': json.dumps(cat_counts),
    }

    return render(request, 'dashboard/admin_dashboard.html', context)


# ======================================================================
# 2. Seller Inline Activation / Deactivation Actions
# ======================================================================

@admin_required
def admin_seller_activate(request, user_id):
    """
    Action to approve and activate a pending seller.
    POST /dashboard/sellers/<user_id>/activate/
    """
    profile = get_object_or_404(UserProfile, userid=user_id, role__role__iexact='seller')
    profile.status = 'Active'
    profile.login.is_active = True
    profile.login.save()
    profile.save()
    messages.success(request, f"Seller account '{profile.contactname}' (@{profile.username}) is now ACTIVATED!")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard:admin_dashboard'))


@admin_required
def admin_seller_deactivate(request, user_id):
    """
    Action to deactivate / revoke a seller's selling privileges.
    POST /dashboard/sellers/<user_id>/deactivate/
    """
    profile = get_object_or_404(UserProfile, userid=user_id, role__role__iexact='seller')
    profile.status = 'Inactive'
    profile.save()
    messages.warning(request, f"Seller account '{profile.contactname}' (@{profile.username}) has been DEACTIVATED.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard:admin_dashboard'))


# ======================================================================
# 3. Manage Users Console (View, Block / Unblock, Role Filters)
# ======================================================================

@admin_required
def admin_users(request):
    """
    Manage Users Table:
    - View all registered users across all roles (Admin, Seller, Buyer)
    - Search by username, contact name, email, phone
    - Filter by Role (Admin, Seller, Buyer) and Status (Active, Inactive, Pending)
    - Actions: Block / Unblock toggle, Activate Seller
    """
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    profiles_qs = UserProfile.objects.select_related(
        'login', 'role', 'state', 'district', 'location'
    ).order_by('-userid')

    # Total counts for KPI badges
    total_all_users = profiles_qs.count()
    active_users_count = profiles_qs.filter(status='Active').count()
    inactive_users_count = profiles_qs.filter(status='Inactive').count()
    pending_users_count = profiles_qs.filter(status='Pending').count()

    # Search filter
    if query:
        profiles_qs = profiles_qs.filter(
            Q(username__icontains=query) |
            Q(contactname__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    # Role filter
    if role_filter:
        profiles_qs = profiles_qs.filter(role__role__iexact=role_filter)

    # Status filter
    if status_filter:
        profiles_qs = profiles_qs.filter(status__iexact=status_filter)

    roles = Role.objects.all().order_by('role')
    paginator = Paginator(profiles_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/admin_users.html', {
        'page_obj': page_obj,
        'roles': roles,
        'query': query,
        'selected_role': role_filter,
        'selected_status': status_filter,
        'total_all_users': total_all_users,
        'active_users_count': active_users_count,
        'inactive_users_count': inactive_users_count,
        'pending_users_count': pending_users_count,
        'active_menu': 'users',
        'page_title': 'Manage Users & Permissions | Admin Console',
    })


@admin_required
def admin_user_toggle_status(request, user_id):
    """
    Action to Block or Unblock a user.
    - If Active -> Sets status='Inactive', login.is_active=False
    - If Inactive -> Sets status='Active', login.is_active=True
    - Safeguard: Prevents an administrator from blocking their own account.
    """
    profile = get_object_or_404(UserProfile.objects.select_related('login', 'role'), userid=user_id)

    if profile.login == request.user:
        messages.error(request, "Security Protection: You cannot suspend or block your own administrator account!")
        return redirect('dashboard:admin_users')

    if profile.status == 'Active':
        profile.status = 'Inactive'
        profile.login.is_active = False
        profile.login.save()
        profile.save()
        messages.warning(
            request,
            f"User account '{profile.username}' ({profile.contactname}) has been BLOCKED. Login access revoked."
        )
    else:
        profile.status = 'Active'
        profile.login.is_active = True
        profile.login.save()
        profile.save()
        messages.success(
            request,
            f"User account '{profile.username}' ({profile.contactname}) has been UNBLOCKED and restored to Active status."
        )

    return redirect(request.META.get('HTTP_REFERER', 'dashboard:admin_users'))


# ======================================================================
# 4. Reports Hub & Date Filter Utilities
# ======================================================================

def parse_date_filters(request):
    """Helper to extract and validate optional start_date and end_date query params."""
    start_str = request.GET.get('start_date', '').strip()
    end_str = request.GET.get('end_date', '').strip()
    start_date = None
    end_date = None

    if start_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = None

    if end_str:
        try:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = None

    return start_date, end_date, start_str, end_str


@admin_required
def admin_reports_hub(request):
    """Landing directory listing all 6 operational reports with quick overview cards."""
    return render(request, 'dashboard/admin_reports_hub.html', {
        'page_title': 'Audit Reports & Analytics Hub | Admin Console',
        'active_menu': 'reports',
    })


# ======================================================================
# 5. Report 1: Users Report
# ======================================================================

@admin_required
def admin_report_users(request):
    """
    Users Master Report:
    Columns: User ID, Username, Contact Name, Role, Email, Phone, Location, Status, Date Joined.
    Supports role filter, status filter, start/end date range on user registration date.
    Exports to CSV and ReportLab PDF.
    """
    start_date, end_date, start_str, end_str = parse_date_filters(request)
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    qs = UserProfile.objects.select_related('login', 'role', 'state', 'district').order_by('-userid')

    if start_date:
        qs = qs.filter(login__date_joined__date__gte=start_date)
    if end_date:
        qs = qs.filter(login__date_joined__date__lte=end_date)
    if role_filter:
        qs = qs.filter(role__role__iexact=role_filter)
    if status_filter:
        qs = qs.filter(status__iexact=status_filter)

    total_records = qs.count()
    roles = Role.objects.all().order_by('role')

    # Export CSV
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_users_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel
        writer = csv.writer(response)
        writer.writerow(['User ID', 'Username', 'Contact Name', 'Role', 'Email', 'Phone', 'Location', 'Status', 'Date Joined'])
        for p in qs:
            loc = f"{p.district.dist}, {p.state.state}" if (p.district and p.state) else "India"
            writer.writerow([
                p.userid, p.username, p.contactname, p.role.role, p.email, p.phone,
                loc, p.status, p.login.date_joined.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    # Export PDF
    if export_format == 'pdf':
        headers = ['ID', 'Username', 'Contact Name', 'Role', 'Email', 'Phone', 'Location', 'Status', 'Joined']
        rows = []
        for p in qs:
            loc = f"{p.district.dist}" if p.district else "India"
            rows.append([
                p.userid, p.username, p.contactname, p.role.role, p.email, p.phone,
                loc, p.status, p.login.date_joined.strftime('%d-%b-%Y')
            ])
        pdf_bytes = build_report_pdf(
            report_title="Users & Access Directory Report",
            subtitle="Registered Collectors, Sellers, and Platform Administrators",
            metadata_dict={
                'Generated By': f"Admin @{request.user.username}",
                'Timestamp': timezone.now().strftime('%d-%b-%Y %H:%M IST'),
                'Date Range': f"{start_str or 'Earliest'} to {end_str or 'Latest'}",
                'Role Filter': role_filter or 'All Roles',
            },
            summary_kpis=[
                ('Total Users', str(total_records)),
                ('Active Users', str(qs.filter(status='Active').count())),
                ('Pending Approvals', str(qs.filter(status='Pending').count())),
                ('Suspended', str(qs.filter(status='Inactive').count())),
            ],
            headers=headers,
            data_rows=rows,
            col_widths=[30, 80, 110, 60, 150, 80, 80, 60, 80]
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_users_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin_report_detail.html', {
        'report_type': 'users',
        'report_title': 'Users & Role Membership Report',
        'report_description': 'Audit profile records, contact data, assigned roles, and account statuses.',
        'page_obj': page_obj,
        'total_records': total_records,
        'roles': roles,
        'start_str': start_str,
        'end_str': end_str,
        'selected_role': role_filter,
        'selected_status': status_filter,
        'active_menu': 'reports',
        'page_title': 'Users Report | Admin Reports',
    })


# ======================================================================
# 6. Report 2: Items Report
# ======================================================================

@admin_required
def admin_report_items(request):
    """
    Antique Catalogue Items Report:
    Columns: SKU, Title, Category, SubCategory, Seller, Age (Yrs), Base Price, Cur Stock, Status, Listed Date.
    Supports category filter, status filter, and date filters on item post date.
    """
    start_date, end_date, start_str, end_str = parse_date_filters(request)
    cat_id = request.GET.get('category_id', '').strip()
    status_filter = request.GET.get('status', '').strip()

    qs = Item.objects.select_related(
        'category', 'subcategory', 'seller', 'seller__userprofile'
    ).prefetch_related('stock_records').order_by('-itemid')

    if start_date:
        qs = qs.filter(post_date__date__gte=start_date)
    if end_date:
        qs = qs.filter(post_date__date__lte=end_date)
    if cat_id and cat_id.isdigit():
        qs = qs.filter(category_id=int(cat_id))
    if status_filter:
        qs = qs.filter(status__iexact=status_filter)

    total_records = qs.count()
    total_val = qs.aggregate(tot=Sum('price'))['tot'] or Decimal('0.00')
    categories = Category.objects.all().order_by('category')

    # Export CSV
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_items_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Item SKU', 'Title', 'Category', 'SubCategory', 'Seller', 'Age (Yrs)', 'Price (INR)', 'Stock', 'Status', 'Post Date'])
        for it in qs:
            writer.writerow([
                it.item, it.title, it.category.category,
                it.subcategory.subcategory if it.subcategory else "-",
                it.seller.username, it.years_old, it.price, it.current_stock,
                it.status, it.post_date.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    # Export PDF
    if export_format == 'pdf':
        headers = ['SKU', 'Title', 'Category', 'Seller', 'Age', 'Price (INR)', 'Stock', 'Status', 'Listed Date']
        rows = []
        for it in qs:
            rows.append([
                it.item, it.title[:30], it.category.category[:20], it.seller.username,
                f"{it.years_old}y", f"₹{it.price}", it.current_stock, it.status,
                it.post_date.strftime('%d-%b-%Y')
            ])
        pdf_bytes = build_report_pdf(
            report_title="Antique Catalogue & Artifacts Inventory Report",
            subtitle="Verified Historical Artifacts, Valuations, and Current Marketplace Status",
            metadata_dict={
                'Generated By': f"Admin @{request.user.username}",
                'Timestamp': timezone.now().strftime('%d-%b-%Y %H:%M IST'),
                'Date Range': f"{start_str or 'Earliest'} to {end_str or 'Latest'}",
            },
            summary_kpis=[
                ('Total Artifacts', str(total_records)),
                ('Catalog Valuation', f"₹{total_val:,.2f}"),
                ('Available', str(qs.filter(status='Available').count())),
                ('Out of Stock', str(qs.filter(status='Out of Stock').count())),
            ],
            headers=headers,
            data_rows=rows,
            col_widths=[75, 175, 110, 80, 45, 80, 50, 65, 80]
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_items_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin_report_detail.html', {
        'report_type': 'items',
        'report_title': 'Antique Catalog & Listings Report',
        'report_description': 'Audit active, out-of-stock, and hidden relics with valuations and seller provenance.',
        'page_obj': page_obj,
        'total_records': total_records,
        'total_val': total_val,
        'categories': categories,
        'start_str': start_str,
        'end_str': end_str,
        'selected_category_id': cat_id,
        'selected_status': status_filter,
        'active_menu': 'reports',
        'page_title': 'Items Report | Admin Reports',
    })


# ======================================================================
# 7. Report 3: Orders Report
# ======================================================================

@admin_required
def admin_report_orders(request):
    """
    Master Orders Report:
    Columns: Order ID, Buyer, Order Date, Items Count, Shipping Charge, Total Amount, Status, Payment Status.
    Filter by status, pay_status, start/end order date.
    """
    start_date, end_date, start_str, end_str = parse_date_filters(request)
    status_filter = request.GET.get('status', '').strip()
    pay_status_filter = request.GET.get('pay_status', '').strip()

    qs = PurchaseMaster.objects.select_related('buyer').prefetch_related('order_items').order_by('-purdate')

    if start_date:
        qs = qs.filter(purdate__date__gte=start_date)
    if end_date:
        qs = qs.filter(purdate__date__lte=end_date)
    if status_filter:
        qs = qs.filter(status__iexact=status_filter)
    if pay_status_filter:
        qs = qs.filter(pay_status__iexact=pay_status_filter)

    total_records = qs.count()
    gross_volume = qs.aggregate(tot=Sum('tot_amt'))['tot'] or Decimal('0.00')

    # Export CSV
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_orders_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Order #', 'Buyer', 'Order Date', 'Items Count', 'Shipping (INR)', 'Total Amount (INR)', 'Fulfillment Status', 'Payment Status'])
        for o in qs:
            writer.writerow([
                o.purchaseid, o.buyer.username, o.purdate.strftime('%Y-%m-%d %H:%M'),
                o.order_items.count(), o.ship_charge, o.tot_amt, o.status, o.pay_status
            ])
        return response

    # Export PDF
    if export_format == 'pdf':
        headers = ['Order #', 'Buyer Username', 'Order Date', 'Items Count', 'Shipping', 'Grand Total', 'Fulfillment', 'Payment']
        rows = []
        for o in qs:
            rows.append([
                f"#{o.purchaseid}", o.buyer.username, o.purdate.strftime('%d-%b-%Y %H:%M'),
                o.order_items.count(), f"₹{o.ship_charge}", f"₹{o.tot_amt}", o.status, o.pay_status
            ])
        pdf_bytes = build_report_pdf(
            report_title="Customer Orders & Procurement Report",
            subtitle="Platform Transactions, Statuses, and Order Fulfillment Audit",
            metadata_dict={
                'Generated By': f"Admin @{request.user.username}",
                'Timestamp': timezone.now().strftime('%d-%b-%Y %H:%M IST'),
                'Date Range': f"{start_str or 'Earliest'} to {end_str or 'Latest'}",
            },
            summary_kpis=[
                ('Total Orders', str(total_records)),
                ('Gross Volume', f"₹{gross_volume:,.2f}"),
                ('Delivered', str(qs.filter(status='Delivered').count())),
                ('Pending / In Transit', str(qs.filter(status__in=['Pending', 'Confirmed', 'Shipped']).count())),
            ],
            headers=headers,
            data_rows=rows,
            col_widths=[60, 110, 120, 60, 70, 90, 80, 70]
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_orders_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin_report_detail.html', {
        'report_type': 'orders',
        'report_title': 'Master Orders Report',
        'report_description': 'Track order fulfillment, buyer IDs, delivery statuses, and order totals.',
        'page_obj': page_obj,
        'total_records': total_records,
        'gross_volume': gross_volume,
        'start_str': start_str,
        'end_str': end_str,
        'selected_status': status_filter,
        'selected_pay_status': pay_status_filter,
        'active_menu': 'reports',
        'page_title': 'Orders Report | Admin Reports',
    })


# ======================================================================
# 8. Report 4: Sales Report
# ======================================================================

@admin_required
def admin_report_sales(request):
    """
    Sales & Net Revenue Report:
    Focused on completed / confirmed sales orders.
    Columns: Order ID, Date, Buyer, Item Titles, Item Subtotal, Shipping, Net Revenue, Pay Method, Pay Status.
    """
    start_date, end_date, start_str, end_str = parse_date_filters(request)
    pay_status_filter = request.GET.get('pay_status', 'Paid').strip()

    qs = PurchaseMaster.objects.select_related(
        'buyer'
    ).prefetch_related('order_items', 'order_items__item').order_by('-purdate')

    # Default to Paid orders for authentic sales reporting, or allow All
    if pay_status_filter and pay_status_filter != 'all':
        qs = qs.filter(pay_status__iexact=pay_status_filter)

    if start_date:
        qs = qs.filter(purdate__date__gte=start_date)
    if end_date:
        qs = qs.filter(purdate__date__lte=end_date)

    total_records = qs.count()
    net_sales = qs.aggregate(tot=Sum('tot_amt'))['tot'] or Decimal('0.00')
    total_shipping = qs.aggregate(tot=Sum('ship_charge'))['tot'] or Decimal('0.00')

    # Export CSV
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_sales_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Order #', 'Date', 'Buyer', 'Items Summary', 'Gross Total (INR)', 'Shipping (INR)', 'Net Revenue (INR)', 'Payment Status'])
        for o in qs:
            items_summary = "; ".join([f"{p.quantity}x {p.item.title}" for p in o.order_items.all()[:3]])
            writer.writerow([
                o.purchaseid, o.purdate.strftime('%Y-%m-%d %H:%M'), o.buyer.username,
                items_summary, o.items_total, o.ship_charge, o.tot_amt, o.pay_status
            ])
        return response

    # Export PDF
    if export_format == 'pdf':
        headers = ['Order #', 'Date', 'Buyer', 'Items Summary', 'Gross Total', 'Shipping', 'Net Revenue', 'Status']
        rows = []
        for o in qs:
            items_summary = ", ".join([f"{p.quantity}x {p.item.title[:20]}" for p in o.order_items.all()[:2]])
            rows.append([
                f"#{o.purchaseid}", o.purdate.strftime('%d-%b-%Y'), o.buyer.username,
                items_summary, f"₹{o.items_total}", f"₹{o.ship_charge}", f"₹{o.tot_amt}", o.pay_status
            ])
        pdf_bytes = build_report_pdf(
            report_title="Platform Sales & Net Revenue Ledger",
            subtitle="Certified Revenue Breakdown, Order Values, and Gross Margins",
            metadata_dict={
                'Generated By': f"Admin @{request.user.username}",
                'Timestamp': timezone.now().strftime('%d-%b-%Y %H:%M IST'),
                'Date Range': f"{start_str or 'Earliest'} to {end_str or 'Latest'}",
            },
            summary_kpis=[
                ('Sales Transactions', str(total_records)),
                ('Net Sales Revenue', f"₹{net_sales:,.2f}"),
                ('Shipping Collected', f"₹{total_shipping:,.2f}"),
                ('Average Order Value', f"₹{(net_sales / total_records if total_records else 0):,.2f}"),
            ],
            headers=headers,
            data_rows=rows,
            col_widths=[60, 80, 100, 200, 80, 70, 90, 80]
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_sales_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin_report_detail.html', {
        'report_type': 'sales',
        'report_title': 'Sales & Revenue Ledger Report',
        'report_description': 'Detailed breakdown of realized antique sales, merchandise subtotals, and shipping fees.',
        'page_obj': page_obj,
        'total_records': total_records,
        'net_sales': net_sales,
        'total_shipping': total_shipping,
        'start_str': start_str,
        'end_str': end_str,
        'selected_pay_status': pay_status_filter,
        'active_menu': 'reports',
        'page_title': 'Sales Report | Admin Reports',
    })


# ======================================================================
# 9. Report 5: Payments Report
# ======================================================================

@admin_required
def admin_report_payments(request):
    """
    Payments Ledger Report:
    Columns: Txn Ref, Order #, Buyer, Method, Bank / Network, Card Last 4, Amount, Status, Date.
    Filter by payment method, payment status, and transaction date range.
    """
    start_date, end_date, start_str, end_str = parse_date_filters(request)
    status_filter = request.GET.get('status', '').strip()
    method_filter = request.GET.get('method', '').strip()

    qs = Payment.objects.select_related('buyer', 'purchase_master').order_by('-pay_date')

    if start_date:
        qs = qs.filter(pay_date__date__gte=start_date)
    if end_date:
        qs = qs.filter(pay_date__date__lte=end_date)
    if status_filter:
        qs = qs.filter(status__iexact=status_filter)
    if method_filter:
        qs = qs.filter(method__iexact=method_filter)

    total_records = qs.count()
    settled_volume = qs.filter(status='Success').aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    # Export CSV
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_payments_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Transaction Ref', 'Order #', 'Buyer', 'Method', 'Bank Name', 'Card Network', 'Card Last 4', 'Amount (INR)', 'Status', 'Date'])
        for p in qs:
            writer.writerow([
                p.transaction_ref, p.purchase_master.purchaseid, p.buyer.username,
                p.method, p.bank_name or "-", p.card_type or "-", p.card_last4 or "-",
                p.amount, p.status, p.pay_date.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    # Export PDF
    if export_format == 'pdf':
        headers = ['Txn Reference', 'Order #', 'Buyer', 'Method', 'Bank / Network', 'Card Last 4', 'Amount', 'Status', 'Date']
        rows = []
        for p in qs:
            rows.append([
                p.transaction_ref, f"#{p.purchase_master.purchaseid}", p.buyer.username,
                p.method, p.bank_name or p.card_type or "COD", f"****{p.card_last4}" if p.card_last4 else "-",
                f"₹{p.amount}", p.status, p.pay_date.strftime('%d-%b-%Y %H:%M')
            ])
        pdf_bytes = build_report_pdf(
            report_title="Financial Payments & Gateway Audit Report",
            subtitle="Settled Transactions, PCI-DSS Compliant Records, and Payment Gateways",
            metadata_dict={
                'Generated By': f"Admin @{request.user.username}",
                'Timestamp': timezone.now().strftime('%d-%b-%Y %H:%M IST'),
                'Date Range': f"{start_str or 'Earliest'} to {end_str or 'Latest'}",
            },
            summary_kpis=[
                ('Total Transactions', str(total_records)),
                ('Settled Amount', f"₹{settled_volume:,.2f}"),
                ('Successful', str(qs.filter(status='Success').count())),
                ('Pending / Failed', str(qs.exclude(status='Success').count())),
            ],
            headers=headers,
            data_rows=rows,
            col_widths=[110, 60, 90, 80, 110, 65, 80, 65, 100]
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_payments_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin_report_detail.html', {
        'report_type': 'payments',
        'report_title': 'Financial Payments & Transactions Report',
        'report_description': 'Audit gateway transactions, card tokens, bank networks, and settled payments.',
        'page_obj': page_obj,
        'total_records': total_records,
        'settled_volume': settled_volume,
        'start_str': start_str,
        'end_str': end_str,
        'selected_status': status_filter,
        'selected_method': method_filter,
        'active_menu': 'reports',
        'page_title': 'Payments Report | Admin Reports',
    })


# ======================================================================
# 10. Report 6: Stock Report
# ======================================================================

@admin_required
def admin_report_stock(request):
    """
    Inventory & Stock Valuation Report:
    Columns: Item SKU, Title, Category, Seller, Arrived Units, Current Units, Stock Status, Low Stock Alert, Last Stock Date.
    Filter by stock status (In Stock, Low Stock, Out of Stock), category, and restock date range.
    """
    start_date, end_date, start_str, end_str = parse_date_filters(request)
    status_filter = request.GET.get('status', '').strip()
    cat_id = request.GET.get('category_id', '').strip()

    qs = Stock.objects.select_related(
        'item', 'item__category', 'item__seller', 'item__seller__userprofile'
    ).order_by('-stockdate')

    if start_date:
        qs = qs.filter(stockdate__date__gte=start_date)
    if end_date:
        qs = qs.filter(stockdate__date__lte=end_date)
    if cat_id and cat_id.isdigit():
        qs = qs.filter(item__category_id=int(cat_id))

    if status_filter == 'low_stock':
        qs = qs.filter(cur_stock__gt=0, cur_stock__lte=Stock.LOW_STOCK_THRESHOLD)
    elif status_filter == 'out_of_stock':
        qs = qs.filter(cur_stock=0)
    elif status_filter == 'in_stock':
        qs = qs.filter(cur_stock__gt=Stock.LOW_STOCK_THRESHOLD)

    total_records = qs.count()
    total_available_units = qs.aggregate(tot=Sum('cur_stock'))['tot'] or 0
    total_arrived_units = qs.aggregate(tot=Sum('tot_arr_stock'))['tot'] or 0
    categories = Category.objects.all().order_by('category')

    # Export CSV
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_stock_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Stock ID', 'Item SKU', 'Title', 'Category', 'Seller', 'Total Arrived', 'Current Available', 'Status', 'Low Stock Alert', 'Last Restocked'])
        for s in qs:
            alert = "YES (Threshold <= 2)" if s.is_low_stock else "NO"
            writer.writerow([
                s.stockid, s.item.item, s.item.title, s.item.category.category,
                s.item.seller.username, s.tot_arr_stock, s.cur_stock,
                s.status, alert, s.stockdate.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    # Export PDF
    if export_format == 'pdf':
        headers = ['SKU', 'Title', 'Category', 'Seller', 'Total Arrived', 'Current Stock', 'Status', 'Low Stock Alert', 'Updated Date']
        rows = []
        for s in qs:
            alert = "LOW STOCK" if s.is_low_stock else ("DEPLETED" if s.is_out_of_stock else "OK")
            rows.append([
                s.item.item, s.item.title[:25], s.item.category.category[:20], s.item.seller.username,
                s.tot_arr_stock, s.cur_stock, s.status, alert, s.stockdate.strftime('%d-%b-%Y')
            ])
        pdf_bytes = build_report_pdf(
            report_title="Inventory Stock Ledger & Depletion Audit",
            subtitle="Warehouse Inventory, Arrived Units, Real-Time Depletion, and Threshold Alerts",
            metadata_dict={
                'Generated By': f"Admin @{request.user.username}",
                'Timestamp': timezone.now().strftime('%d-%b-%Y %H:%M IST'),
                'Date Range': f"{start_str or 'Earliest'} to {end_str or 'Latest'}",
            },
            summary_kpis=[
                ('Tracked Relics', str(total_records)),
                ('Available Units', f"{total_available_units:,}"),
                ('Total Arrived Units', f"{total_arrived_units:,}"),
                ('Depletion / Out of Stock', str(qs.filter(cur_stock=0).count())),
            ],
            headers=headers,
            data_rows=rows,
            col_widths=[75, 175, 110, 80, 60, 60, 60, 70, 70]
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="antique_hub_stock_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin_report_detail.html', {
        'report_type': 'stock',
        'report_title': 'Inventory & Stock Depletion Report',
        'report_description': 'Track arrived vs current units, restock histories, and low-stock warning triggers.',
        'page_obj': page_obj,
        'total_records': total_records,
        'total_available_units': total_available_units,
        'total_arrived_units': total_arrived_units,
        'categories': categories,
        'start_str': start_str,
        'end_str': end_str,
        'selected_category_id': cat_id,
        'selected_status': status_filter,
        'active_menu': 'reports',
        'page_title': 'Stock Report | Admin Reports',
    })
