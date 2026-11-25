"""
Orders & Cart Views for Antique Hub (Module 7).
Handles:
- Cart management (add, update quantity, remove with confirmation, cart summary)
- Order placement & atomic checkout (PurchaseMaster & Purchase creation, transactional row-locking stock reduction)
- Buyer "My Orders" and "Track Order Status" with interactive timeline
- Buyer order cancellation before shipment with automatic restocking
- Seller "View Orders" for items listed by the seller
- Admin Master Order Management (DFD 5.1 to 5.3: view all, activate/confirm, ship, deliver, cancel)
- Business rules: Prevent self-purchase, prevent overselling, enforce stock limits
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q

from accounts.decorators import admin_required, seller_required
from catalog.models import Item
from inventory.models import Stock, InsufficientStockError
from .models import Cart, PurchaseMaster, Purchase


def get_cart_summary(buyer):
    """
    Computes cart financial summary:
    - items_count: total units
    - items_total: gross original MRP sum
    - discount_total: total promotional savings
    - subtotal: net price after discount
    - shipping_charge: flat ₹250, or ₹0 if subtotal >= 50,000 (free insured shipping)
    - grand_total: subtotal + shipping_charge
    """
    cart_items = Cart.objects.filter(buyer=buyer).select_related(
        'item',
        'item__category',
        'item__subcategory',
        'item__seller',
        'item__seller__userprofile',
        'item__seller__userprofile__location',
        'item__seller__userprofile__district',
        'item__seller__userprofile__state',
    ).prefetch_related(
        'item__category__discounts',
        'item__stock_records',
    ).order_by('-added_date')

    items_count = sum(ci.quantity for ci in cart_items)
    items_total = sum(ci.original_subtotal for ci in cart_items)
    subtotal = sum(ci.subtotal for ci in cart_items)
    discount_total = sum(ci.discount_saved for ci in cart_items)

    if subtotal > 0:
        shipping_charge = Decimal('0.00') if subtotal >= Decimal('50000.00') else Decimal('250.00')
    else:
        shipping_charge = Decimal('0.00')

    grand_total = subtotal + shipping_charge

    return {
        'cart_items': cart_items,
        'items_count': items_count,
        'items_total': round(items_total, 2),
        'discount_total': round(discount_total, 2),
        'subtotal': round(subtotal, 2),
        'shipping_charge': shipping_charge,
        'grand_total': round(grand_total, 2),
        'free_shipping_eligible': subtotal >= Decimal('50000.00'),
    }


# ======================================================================
# 1. Cart Management Views (Module 7)
# ======================================================================

@login_required
def cart_view(request):
    """
    Displays the buyer's shopping cart with itemized rows, active discounts,
    stock warnings, shipping charge, and order summary.
    """
    summary = get_cart_summary(request.user)
    return render(request, 'orders/cart.html', {
        **summary,
        'page_title': 'Heritage Shopping Cart | Antique Hub',
    })


@login_required
def add_to_cart(request, item_id):
    """
    Adds an antique item to the buyer's cart with validation:
    1. Stop a buyer from buying their own item!
    2. Check availability and stock balance.
    3. Ensure requested quantity does not exceed current stock.
    """
    item = get_object_or_404(Item, itemid=item_id)

    # Business Rule: Stop a seller from buying their own item
    if item.seller == request.user:
        messages.error(request, "You cannot purchase your own antique listing.")
        return redirect('catalog:item_detail', item_id=item.itemid)

    # Check status and stock
    available_stock = item.current_stock
    if item.status != 'Available' or available_stock <= 0:
        messages.error(request, f"'{item.title}' is currently out of stock and cannot be added to cart.")
        return redirect('catalog:item_detail', item_id=item.itemid)

    quantity = 1
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1

    cart_entry, created = Cart.objects.get_or_create(
        buyer=request.user,
        item=item,
        defaults={'quantity': min(quantity, available_stock)}
    )

    if not created:
        new_quantity = cart_entry.quantity + quantity
        if new_quantity > available_stock:
            cart_entry.quantity = available_stock
            cart_entry.save()
            messages.warning(
                request,
                f"Cart updated to maximum available stock ({available_stock} units) for '{item.title}'."
            )
        else:
            cart_entry.quantity = new_quantity
            cart_entry.save()
            messages.success(request, f"Updated '{item.title}' quantity to {cart_entry.quantity} in your Cart.")
    else:
        if quantity > available_stock:
            messages.warning(
                request,
                f"Added maximum available stock ({available_stock} units) for '{item.title}' to your Cart."
            )
        else:
            messages.success(request, f"'{item.title}' has been added to your Cart!")

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('orders:cart_view')


@login_required
def update_cart_quantity(request, cart_id):
    """
    Updates the quantity of a specific cart item.
    Enforces that quantity cannot exceed current available stock.
    """
    cart_entry = get_object_or_404(Cart, cartid=cart_id, buyer=request.user)

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            new_quantity = 1

        available_stock = cart_entry.item.current_stock

        if new_quantity <= 0:
            cart_entry.delete()
            messages.info(request, f"'{cart_entry.item.title}' removed from your cart.")
        elif new_quantity > available_stock:
            messages.error(
                request,
                f"Cannot update to {new_quantity} units. Only {available_stock} unit(s) available in stock."
            )
        else:
            cart_entry.quantity = new_quantity
            cart_entry.save()
            messages.success(request, f"Updated quantity for '{cart_entry.item.title}' to {new_quantity}.")

    return redirect('orders:cart_view')


@login_required
def remove_from_cart(request, cart_id):
    """
    Removes an item from cart with confirmation (DFD 1.2.1).
    GET -> Confirmation page
    POST -> Deletes cart entry
    """
    cart_entry = get_object_or_404(
        Cart.objects.select_related('item', 'item__category'),
        cartid=cart_id,
        buyer=request.user
    )

    if request.method == 'POST':
        item_title = cart_entry.item.title
        cart_entry.delete()
        messages.success(request, f"'{item_title}' has been removed from your cart.")
        return redirect('orders:cart_view')

    return render(request, 'orders/cart_confirm_remove.html', {
        'cart_entry': cart_entry,
        'page_title': f"Remove {cart_entry.item.title} | Cart",
    })


# ======================================================================
# 2. Checkout & Order Placement (Atomic Transaction & Row Locking - DFD 1.3, 1.3.1)
# ======================================================================

@login_required
def confirm_order(request):
    """
    Places and confirms the order (DFD 1.3 & 1.3.1).
    - Checks cart is not empty.
    - Validates no self-purchases.
    - Uses an atomic database transaction (@transaction.atomic).
    - Reduces stock for each item using Stock.reduce_stock() with select_for_update() row locking!
    - Creates PurchaseMaster (status='Pending', pay_status='Unpaid').
    - Creates Purchase rows for each item.
    - Clears the buyer's cart.
    - Catches InsufficientStockError and rolls back gracefully if stock was exhausted.
    """
    if request.method != 'POST':
        return redirect('orders:cart_view')

    summary = get_cart_summary(request.user)
    cart_items = summary['cart_items']

    if not cart_items:
        messages.error(request, "Your cart is empty. Please add antique items before placing an order.")
        return redirect('catalog:item_list')

    # Self-purchase check
    for ci in cart_items:
        if ci.item.seller == request.user:
            messages.error(
                request,
                f"You cannot purchase your own listing '{ci.item.title}'. Please remove it from your cart."
            )
            return redirect('orders:cart_view')

    try:
        with transaction.atomic():
            # 1. Reduce stock for each item using atomic row locking (select_for_update)
            for ci in cart_items:
                Stock.reduce_stock(item_id=ci.item.itemid, quantity=ci.quantity)

            # 2. Create PurchaseMaster record
            purchase_master = PurchaseMaster.objects.create(
                buyer=request.user,
                ship_charge=summary['shipping_charge'],
                tot_amt=summary['grand_total'],
                status='Pending',
                pay_status='Unpaid'
            )

            # 3. Create Purchase line items with snapshotted effective price paid per unit
            purchase_rows = [
                Purchase(
                    purchase_master=purchase_master,
                    item=ci.item,
                    quantity=ci.quantity,
                    price=ci.unit_price
                )
                for ci in cart_items
            ]
            Purchase.objects.bulk_create(purchase_rows)

            # 4. Clear buyer's cart
            Cart.objects.filter(buyer=request.user).delete()

    except InsufficientStockError as e:
        messages.error(request, f"Order placement failed: {str(e)}")
        return redirect('orders:cart_view')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred while placing your order: {str(e)}")
        return redirect('orders:cart_view')

    messages.success(
        request,
        f"Order #{purchase_master.purchaseid} placed successfully! Status: Pending (Unpaid)."
    )
    return redirect('orders:order_detail', purchase_id=purchase_master.purchaseid)


# ======================================================================
# 3. Buyer Orders & Tracking Page with Timeline
# ======================================================================

@login_required
def buyer_orders(request):
    """
    Buyer "My Orders" listing page.
    Displays all orders placed by the authenticated buyer, with status, date, items, and total.
    """
    orders_qs = PurchaseMaster.objects.filter(buyer=request.user).prefetch_related(
        'order_items__item',
        'order_items__item__category'
    ).order_by('-purdate')

    paginator = Paginator(orders_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/buyer_order_list.html', {
        'page_obj': page_obj,
        'page_title': 'My Orders | Antique Hub',
    })


@login_required
def order_detail(request, purchase_id):
    """
    Detailed Order View & Status Timeline tracking.
    Accessible by:
    - Order Buyer
    - Seller who sold items in this order
    - Admin
    Shows:
    - Status Timeline (Pending → Confirmed → Shipped → Delivered / Cancelled)
    - Itemized breakdown (photograph, title, seller location, quantity, subtotal)
    - Shipping charge and Grand total
    - Buyer Cancellation button (if status in ['Pending', 'Confirmed'])
    """
    order = get_object_or_404(
        PurchaseMaster.objects.select_related(
            'buyer',
            'buyer__userprofile',
            'buyer__userprofile__location',
            'buyer__userprofile__district',
            'buyer__userprofile__state',
        ).prefetch_related(
            'order_items__item',
            'order_items__item__category',
            'order_items__item__seller',
            'order_items__item__seller__userprofile',
            'order_items__item__seller__userprofile__location',
            'order_items__item__seller__userprofile__district',
            'order_items__item__seller__userprofile__state',
        ),
        purchaseid=purchase_id
    )

    # Permission check: buyer, seller of items, or admin
    is_admin = request.user.is_superuser or request.user.is_staff or (
        hasattr(request.user, 'userprofile') and request.user.userprofile.role.role.lower() == 'admin'
    )
    is_buyer = order.buyer == request.user
    is_seller = order.order_items.filter(item__seller=request.user).exists()

    if not (is_admin or is_buyer or is_seller):
        raise PermissionDenied("You do not have permission to view this antique order.")

    # Timeline calculation
    status_order = ['Pending', 'Confirmed', 'Shipped', 'Delivered']
    current_status = order.status
    current_step_index = status_order.index(current_status) if current_status in status_order else -1
    is_cancelled = current_status == 'Cancelled'

    # Can cancel if buyer and status in ['Pending', 'Confirmed']
    can_cancel = is_buyer and current_status in ['Pending', 'Confirmed']

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'current_step_index': current_step_index,
        'is_cancelled': is_cancelled,
        'can_cancel': can_cancel,
        'is_admin': is_admin,
        'is_seller': is_seller,
        'is_buyer': is_buyer,
        'status_choices': PurchaseMaster.STATUS_CHOICES,
        'page_title': f"Order #{order.purchaseid} Status & Details | Antique Hub",
    })


@login_required
def cancel_order(request, purchase_id):
    """
    Buyer cancellation before shipment.
    Restocks each ordered item atomically and marks order Cancelled.
    """
    order = get_object_or_404(PurchaseMaster, purchaseid=purchase_id)

    # Permission check: only buyer or admin can cancel
    is_admin = request.user.is_superuser or request.user.is_staff
    if not (is_admin or order.buyer == request.user):
        raise PermissionDenied("You do not have permission to cancel this order.")

    if order.status not in ['Pending', 'Confirmed']:
        messages.error(
            request,
            f"Cannot cancel order #{order.purchaseid}. Orders that are '{order.status}' cannot be cancelled."
        )
        return redirect('orders:order_detail', purchase_id=order.purchaseid)

    if request.method == 'POST':
        with transaction.atomic():
            # Restock each item
            for order_item in order.order_items.select_related('item').all():
                stock = Stock.objects.filter(item=order_item.item).first()
                if stock:
                    stock.add_stock(order_item.quantity)

            order.status = 'Cancelled'
            if order.pay_status == 'Paid':
                order.pay_status = 'Refunded'
            order.save(update_fields=['status', 'pay_status'])

        messages.success(
            request,
            f"Order #{order.purchaseid} has been cancelled successfully. All items have been returned to available stock."
        )

    return redirect('orders:order_detail', purchase_id=order.purchaseid)


# ======================================================================
# 4. Seller Orders View
# ======================================================================

@seller_required
def seller_orders(request):
    """
    Seller "View Orders" showing orders that contain items listed by this seller.
    """
    seller_purchases = Purchase.objects.filter(
        item__seller=request.user
    ).select_related(
        'purchase_master',
        'purchase_master__buyer',
        'purchase_master__buyer__userprofile',
        'item',
        'item__category'
    ).order_by('-purchase_master__purdate')

    paginator = Paginator(seller_purchases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/seller_order_list.html', {
        'page_obj': page_obj,
        'page_title': 'Orders on My Artifacts | Seller Hub',
    })


# ======================================================================
# 5. Admin Master Order Management (DFD 5.1 to 5.3)
# ======================================================================

@admin_required
def admin_orders(request):
    """
    Admin Master Order Management table (DFD 5.1 to 5.3).
    Supervises all orders across all buyers and sellers with search,
    status filtering, and quick actions.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    pay_status_filter = request.GET.get('pay_status', '').strip()

    orders_qs = PurchaseMaster.objects.select_related(
        'buyer',
        'buyer__userprofile'
    ).prefetch_related(
        'order_items__item'
    ).order_by('-purdate')

    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    if pay_status_filter:
        orders_qs = orders_qs.filter(pay_status=pay_status_filter)

    if query:
        orders_qs = orders_qs.filter(
            Q(purchaseid__icontains=query) |
            Q(buyer__username__icontains=query) |
            Q(buyer__email__icontains=query) |
            Q(buyer__userprofile__contactname__icontains=query)
        )

    paginator = Paginator(orders_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/admin_order_list.html', {
        'page_obj': page_obj,
        'selected_status': status_filter,
        'selected_pay_status': pay_status_filter,
        'query': query,
        'status_choices': PurchaseMaster.STATUS_CHOICES,
        'pay_status_choices': PurchaseMaster.PAY_STATUS_CHOICES,
        'page_title': 'Master Order Management | Admin Console',
    })


@admin_required
def admin_update_status(request, purchase_id):
    """
    Admin updates order status (DFD 5.1 activate/confirm, 5.2 shipped, 5.3 delivered / cancelled).
    If updated to Cancelled from an active status, restocks the items atomically.
    """
    order = get_object_or_404(PurchaseMaster, purchaseid=purchase_id)

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        new_pay_status = request.POST.get('pay_status', '').strip()

        valid_statuses = [choice[0] for choice in PurchaseMaster.STATUS_CHOICES]
        valid_pay_statuses = [choice[0] for choice in PurchaseMaster.PAY_STATUS_CHOICES]

        if new_status in valid_statuses:
            old_status = order.status
            # If changing from active to Cancelled, restock items
            if new_status == 'Cancelled' and old_status in ['Pending', 'Confirmed']:
                with transaction.atomic():
                    for order_item in order.order_items.select_related('item').all():
                        stock = Stock.objects.filter(item=order_item.item).first()
                        if stock:
                            stock.add_stock(order_item.quantity)
                    order.status = 'Cancelled'
                    if new_pay_status in valid_pay_statuses:
                        order.pay_status = new_pay_status
                    order.save()
                messages.success(request, f"Order #{order.purchaseid} cancelled and items restocked.")
            else:
                order.status = new_status
                if new_pay_status in valid_pay_statuses:
                    order.pay_status = new_pay_status
                order.save()
                messages.success(request, f"Order #{order.purchaseid} status updated to '{new_status}'.")
        else:
            messages.error(request, "Invalid order status specified.")

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('orders:order_detail', purchase_id=order.purchaseid)
