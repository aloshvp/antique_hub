"""
Inventory utilities and centralized pricing calculation functions.
Module 12: One single authoritative helper function for effective price calculation
used consistently across listings, item detail, cart, checkout, and order history.
"""

from decimal import Decimal
from django.utils import timezone
from django.db.models import Q


def get_effective_price(item, as_of_date=None):
    """
    Central helper function to calculate the effective price of an antique artifact.
    Guarantees consistent pricing logic across:
    - Marketplace catalogue and home listings
    - Item detail pages
    - Cart items and cart summary calculations
    - Order checkout and order placement
    - Discount search and buyer collections

    Handles:
    - Active promotional discounts on specific categories
    - Store-wide discounts (applicable_cat is NULL)
    - Highest discount selection if multiple apply
    - Automatic expiry when today's date exceeds enddate

    Returns:
        dict containing:
        - 'original_price': Decimal original artifact price
        - 'effective_price': Decimal final payable price (after discount)
        - 'discount_percent': Decimal discount percentage (0 if no discount)
        - 'has_discount': bool
        - 'active_discount': Discount instance or None
        - 'savings': Decimal amount saved per unit
    """
    if not item:
        return {
            'original_price': Decimal('0.00'),
            'effective_price': Decimal('0.00'),
            'discount_percent': Decimal('0.00'),
            'has_discount': False,
            'active_discount': None,
            'savings': Decimal('0.00'),
        }

    from inventory.models import Discount

    try:
        orig_price = Decimal(str(item.price))
    except (ValueError, TypeError):
        orig_price = Decimal('0.00')

    target_date = as_of_date or timezone.localdate()

    # Query active discounts where startdate <= target_date <= enddate
    discounts_qs = Discount.objects.filter(
        startdate__lte=target_date,
        enddate__gte=target_date
    )

    if hasattr(item, 'category_id') and item.category_id:
        discounts_qs = discounts_qs.filter(
            Q(applicable_cat_id=item.category_id) | Q(applicable_cat__isnull=True)
        )
    else:
        discounts_qs = discounts_qs.filter(applicable_cat__isnull=True)

    # Take highest discount percentage if multiple apply
    best_discount = discounts_qs.order_by('-discount_percent').first()

    if best_discount and best_discount.discount_percent > 0:
        percent = Decimal(str(best_discount.discount_percent))
        # Ensure percent does not exceed 90% or fall below 1%
        percent = min(Decimal('90.00'), max(Decimal('1.00'), percent))
        savings = round(orig_price * (percent / Decimal('100')), 2)
        effective_price = round(orig_price - savings, 2)
        return {
            'original_price': orig_price,
            'effective_price': effective_price,
            'discount_percent': percent,
            'has_discount': True,
            'active_discount': best_discount,
            'discount': best_discount,
            'savings': savings,
            'discount_saved': savings,
        }

    return {
        'original_price': orig_price,
        'effective_price': orig_price,
        'discount_percent': Decimal('0.00'),
        'has_discount': False,
        'active_discount': None,
        'discount': None,
        'savings': Decimal('0.00'),
        'discount_saved': Decimal('0.00'),
    }
