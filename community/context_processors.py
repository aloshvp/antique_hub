"""
Context processors for Community module (Watchlist badges and state).
Provides active watchlist item IDs and total count for authenticated users.
"""

from .models import WatchListed


def watchlist_context(request):
    """
    Supplies the authenticated user's set of watchlisted item IDs and total count.
    Used for rendering active heart state on artifact cards across all pages.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            ids = list(WatchListed.objects.filter(user=request.user).values_list('item_id', flat=True))
            return {
                'user_watchlist_ids': set(ids),
                'watchlist_count': len(ids),
            }
        except Exception:
            return {
                'user_watchlist_ids': set(),
                'watchlist_count': 0,
            }
    return {
        'user_watchlist_ids': set(),
        'watchlist_count': 0,
    }
