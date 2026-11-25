"""
Payment Views for Antique Hub (Module 8 - Payments).
Handles:
- Demo Sandbox payment checkout (Credit/Debit Card with Luhn validation or Cash on Delivery).
- PCI-DSS compliant storage (only stores last 4 digits, card brand, bank name, amount, date, transaction ID).
- Order pay_status update from 'Unpaid' to 'Paid'.
- Printable Tax Invoice / Payment Receipt.
- Seller "View Payment and Order" with date and status filters.
- Admin "View Payment and Order" master ledger with date, status, method filters.
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils.dateparse import parse_date
from datetime import datetime

from accounts.decorators import admin_required, seller_required
from orders.models import PurchaseMaster, Purchase
from .models import Payment
from .services import get_payment_gateway


INDIAN_BANKS = [
    'State Bank of India',
    'HDFC Bank',
    'ICICI Bank',
    'Axis Bank',
    'Punjab National Bank',
    'Bank of Baroda',
    'Kotak Mahindra Bank',
    'Canara Bank',
    'Union Bank of India',
    'IndusInd Bank',
    'Federal Bank',
    'Reserve Bank Sandbox',
]


@login_required
def checkout_payment(request, order_id):
    """
    Demo Payment Checkout page for an order.
    - Allows buyer to choose Credit Card, Debit Card, or Cash on Delivery (COD).
    - Collects card holder, number, expiry (MM/YY), CVV, and bank name.
    - Validates with Luhn algorithm and expiry date via pluggable Gateway Service.
    - Stores ONLY: last 4 digits, card type, bank name, amount, date, and generated transaction ID.
    - NEVER stores full card number or CVV (PCI-DSS compliance).
    - On success: marks pay_status='Paid', status='Confirmed' (if Pending), and redirects to receipt.
    """
    order = get_object_or_404(
        PurchaseMaster.objects.select_related('buyer', 'buyer__userprofile'),
        purchaseid=order_id
    )

    # Security: Ensure only the buyer (or staff/admin) can pay for this order
    if order.buyer != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied. You can only process payments for your own orders.")
        return redirect('accounts:role_redirect')

    # If order is already paid, redirect straight to receipt
    if order.pay_status == 'Paid':
        messages.info(request, f"Order #{order.purchaseid} has already been paid in full.")
        return redirect('payments:receipt', order_id=order.purchaseid)

    # If order was cancelled, payment is disallowed
    if order.status == 'Cancelled':
        messages.error(request, f"Order #{order.purchaseid} has been cancelled. Payment cannot be processed.")
        return redirect('orders:order_detail', purchase_id=order.purchaseid)

    order_items = order.order_items.select_related('item', 'item__category', 'item__seller')
    gateway = get_payment_gateway()
    current_year = datetime.now().year

    if request.method == 'POST':
        payment_type = request.POST.get('payment_type', 'card').strip()

        if payment_type == 'card':
            card_data = {
                'card_holder': request.POST.get('card_holder'),
                'card_number': request.POST.get('card_number'),
                'exp_month': request.POST.get('exp_month'),
                'exp_year': request.POST.get('exp_year'),
                'cvv': request.POST.get('cvv'),
                'method': request.POST.get('card_method', 'Credit Card'),
                'bank_name': request.POST.get('bank_name'),
            }
            result = gateway.process_card_payment(order, card_data)
        elif payment_type == 'cod':
            result = gateway.process_cod_payment(order)
        else:
            messages.error(request, "Invalid payment method selected.")
            return redirect('payments:checkout_payment', order_id=order.purchaseid)

        if not result.success:
            messages.error(request, f"Payment authorization failed: {result.error_message}")
            return render(request, 'payments/checkout.html', {
                'order': order,
                'order_items': order_items,
                'banks': INDIAN_BANKS,
                'current_year': current_year,
                'year_range': range(current_year, current_year + 16),
                'form_data': request.POST,
                'selected_payment_type': payment_type,
            })

        # Payment Succeeded: Save sanitized record and update order atomically
        with transaction.atomic():
            # Check if payment record already exists (avoid duplicate on re-post)
            payment_record, created = Payment.objects.get_or_create(
                purchase_master=order,
                defaults={
                    'buyer': order.buyer,
                    'amount': result.amount,
                    'method': result.method,
                    'status': result.status,
                    'card_last4': result.card_last4,
                    'card_type': result.card_type,
                    'bank_name': result.bank_name,
                    'transaction_ref': result.transaction_id,
                }
            )
            if not created:
                # Update existing record if it was pending
                payment_record.amount = result.amount
                payment_record.method = result.method
                payment_record.status = result.status
                payment_record.card_last4 = result.card_last4
                payment_record.card_type = result.card_type
                payment_record.bank_name = result.bank_name
                payment_record.transaction_ref = result.transaction_id
                payment_record.save()

            # Update order payment and fulfillment status
            order.pay_status = 'Paid'
            if order.status == 'Pending':
                order.status = 'Confirmed'
            order.save()

        messages.success(
            request,
            f"Payment of ₹{result.amount} authorized successfully! Reference ID: {result.transaction_id}"
        )
        return redirect('payments:receipt', order_id=order.purchaseid)

    return render(request, 'payments/checkout.html', {
        'order': order,
        'order_items': order_items,
        'banks': INDIAN_BANKS,
        'current_year': current_year,
        'year_range': range(current_year, current_year + 16),
        'selected_payment_type': 'card',
    })


@login_required
def receipt(request, order_id):
    """
    Printable Tax Invoice & Payment Receipt view.
    Accessible by the Buyer, Admin, or Seller associated with the order.
    Includes print stylesheet and clean formatting for printing or PDF export.
    """
    order = get_object_or_404(
        PurchaseMaster.objects.select_related('buyer', 'buyer__userprofile'),
        purchaseid=order_id
    )

    # Permission check: Buyer, Admin, or participating Seller
    is_buyer = (order.buyer == request.user)
    is_admin = (request.user.is_staff or request.user.is_superuser)
    is_seller = False

    order_items = order.order_items.select_related(
        'item', 'item__seller', 'item__seller__userprofile', 'item__category'
    )

    if not is_buyer and not is_admin:
        # Check if user is one of the sellers for this order
        seller_ids = [item.item.seller_id for item in order_items]
        if request.user.id in seller_ids:
            is_seller = True
        else:
            messages.error(request, "Access denied. You do not have permission to view this receipt.")
            return redirect('accounts:role_redirect')

    payment = getattr(order, 'payment_record', None)

    # Compute items subtotal before shipping using snapshotted unit prices
    items_subtotal = Decimal('0.00')
    for p in order_items:
        items_subtotal += (p.unit_price * p.quantity)

    return render(request, 'payments/receipt.html', {
        'order': order,
        'payment': payment,
        'order_items': order_items,
        'items_subtotal': items_subtotal,
        'is_buyer': is_buyer,
        'is_admin': is_admin,
        'is_seller': is_seller,
        'today': datetime.now(),
    })


@login_required
@seller_required
def seller_payments(request):
    """
    Seller "View Payment and Order" page with date and status filters.
    Displays orders containing items uploaded by the authenticated seller.
    """
    # Base queryset: orders containing at least one item from this seller
    orders_qs = PurchaseMaster.objects.filter(
        order_items__item__seller=request.user
    ).distinct().select_related(
        'buyer', 'buyer__userprofile', 'payment_record'
    ).prefetch_related(
        'order_items__item'
    ).order_by('-purdate')

    # Filter: Start Date
    start_date_str = request.GET.get('start_date', '').strip()
    if start_date_str:
        s_date = parse_date(start_date_str)
        if s_date:
            orders_qs = orders_qs.filter(purdate__date__gte=s_date)

    # Filter: End Date
    end_date_str = request.GET.get('end_date', '').strip()
    if end_date_str:
        e_date = parse_date(end_date_str)
        if e_date:
            orders_qs = orders_qs.filter(purdate__date__lte=e_date)

    # Filter: Fulfillment Status
    order_status = request.GET.get('order_status', '').strip()
    if order_status:
        orders_qs = orders_qs.filter(status=order_status)

    # Filter: Payment Status
    pay_status = request.GET.get('pay_status', '').strip()
    if pay_status:
        orders_qs = orders_qs.filter(pay_status=pay_status)

    # Search: Order ID or buyer username
    search_query = request.GET.get('search', '').strip()
    if search_query:
        if search_query.isdigit():
            orders_qs = orders_qs.filter(
                Q(purchaseid=int(search_query)) |
                Q(buyer__username__icontains=search_query) |
                Q(order_items__item__title__icontains=search_query)
            ).distinct()
        else:
            orders_qs = orders_qs.filter(
                Q(buyer__username__icontains=search_query) |
                Q(order_items__item__title__icontains=search_query)
            ).distinct()

    # Seller Revenue Metrics (Total revenue on seller's items in Paid orders)
    paid_seller_purchases = Purchase.objects.filter(
        item__seller=request.user,
        purchase_master__pay_status='Paid'
    ).select_related('item')

    # Calculate net earnings for this seller across paid orders using snapshotted unit prices
    total_seller_earnings = Decimal('0.00')
    for p in paid_seller_purchases:
        total_seller_earnings += (p.unit_price * p.quantity)

    total_orders_count = orders_qs.count()
    pending_orders_count = orders_qs.filter(status='Pending').count()

    paginator = Paginator(orders_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/seller_payments.html', {
        'page_obj': page_obj,
        'total_orders_count': total_orders_count,
        'total_seller_earnings': total_seller_earnings,
        'pending_orders_count': pending_orders_count,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'order_status': order_status,
        'pay_status': pay_status,
        'search_query': search_query,
        'status_choices': PurchaseMaster.STATUS_CHOICES,
        'pay_status_choices': PurchaseMaster.PAY_STATUS_CHOICES,
    })


@login_required
@admin_required
def admin_payments(request):
    """
    Admin "View Payment and Order" master ledger with filters by date, status, and method.
    Provides complete oversight of marketplace transaction volume and settlement status.
    """
    orders_qs = PurchaseMaster.objects.select_related(
        'buyer', 'buyer__userprofile', 'payment_record'
    ).prefetch_related(
        'order_items__item'
    ).order_by('-purdate')

    # Date Filters
    start_date_str = request.GET.get('start_date', '').strip()
    if start_date_str:
        s_date = parse_date(start_date_str)
        if s_date:
            orders_qs = orders_qs.filter(purdate__date__gte=s_date)

    end_date_str = request.GET.get('end_date', '').strip()
    if end_date_str:
        e_date = parse_date(end_date_str)
        if e_date:
            orders_qs = orders_qs.filter(purdate__date__lte=e_date)

    # Order Status Filter
    order_status = request.GET.get('order_status', '').strip()
    if order_status:
        orders_qs = orders_qs.filter(status=order_status)

    # Payment Status Filter
    pay_status = request.GET.get('pay_status', '').strip()
    if pay_status:
        orders_qs = orders_qs.filter(pay_status=pay_status)

    # Payment Method Filter
    method = request.GET.get('method', '').strip()
    if method:
        orders_qs = orders_qs.filter(payment_record__method=method)

    # Search Filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        if search_query.isdigit():
            orders_qs = orders_qs.filter(
                Q(purchaseid=int(search_query)) |
                Q(buyer__username__icontains=search_query) |
                Q(payment_record__transaction_ref__icontains=search_query) |
                Q(payment_record__card_last4=search_query) |
                Q(payment_record__bank_name__icontains=search_query)
            )
        else:
            orders_qs = orders_qs.filter(
                Q(buyer__username__icontains=search_query) |
                Q(payment_record__transaction_ref__icontains=search_query) |
                Q(payment_record__bank_name__icontains=search_query)
            )

    # Master Platform Financial Metrics
    total_paid_volume = PurchaseMaster.objects.filter(pay_status='Paid').aggregate(
        total=Sum('tot_amt')
    )['total'] or Decimal('0.00')

    total_unpaid_volume = PurchaseMaster.objects.filter(
        pay_status__in=['Unpaid', 'Pending']
    ).exclude(status='Cancelled').aggregate(
        total=Sum('tot_amt')
    )['total'] or Decimal('0.00')

    total_paid_count = PurchaseMaster.objects.filter(pay_status='Paid').count()
    cod_orders_count = Payment.objects.filter(method='Cash on Delivery').count()

    paginator = Paginator(orders_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/admin_payments.html', {
        'page_obj': page_obj,
        'total_paid_volume': total_paid_volume,
        'total_unpaid_volume': total_unpaid_volume,
        'total_paid_count': total_paid_count,
        'cod_orders_count': cod_orders_count,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'order_status': order_status,
        'pay_status': pay_status,
        'method': method,
        'search_query': search_query,
        'status_choices': PurchaseMaster.STATUS_CHOICES,
        'pay_status_choices': PurchaseMaster.PAY_STATUS_CHOICES,
        'method_choices': Payment.METHOD_CHOICES,
    })
