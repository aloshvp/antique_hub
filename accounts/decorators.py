"""
Role-based Access Control (RBAC) Decorators for Antique Hub.
Used throughout the project to enforce strict permission boundaries
for Admin, Seller, and Buyer roles, including Seller activation checks.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def role_required(allowed_roles, raise_exception=False, require_active_seller=True):
    """
    Decorator for views that checks if the logged-in user belongs to one of
    the allowed roles: 'admin', 'seller', or 'buyer'.
    
    If require_active_seller is True and the role is 'seller', checks that
    UserProfile.status == 'Active'. If 'Pending', redirects to the pending page.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Ensure user is authenticated
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to access this page.")
                return redirect('accounts:login')

            # 2. Staff and superusers always qualify as admin
            if request.user.is_superuser or request.user.is_staff:
                user_role = 'admin'
                user_status = 'Active'
            else:
                profile = getattr(request.user, 'userprofile', None)
                if profile and profile.role:
                    user_role = profile.role.role.lower().strip()
                    user_status = profile.status
                else:
                    user_role = 'buyer'
                    user_status = 'Active'

            # 3. Check role authorization
            normalized_allowed = [r.lower().strip() for r in allowed_roles]
            if user_role not in normalized_allowed:
                if raise_exception:
                    raise PermissionDenied("You do not have permission to access this resource.")
                messages.error(
                    request,
                    f"Access denied. This page is reserved for {', '.join(allowed_roles).title()} accounts."
                )
                return redirect('accounts:role_redirect')

            # 4. Check Seller Activation status (matches DFD 'Activate Seller')
            if user_role == 'seller' and require_active_seller and user_status != 'Active':
                if raise_exception:
                    raise PermissionDenied("Your Seller account is pending Administrator activation.")
                messages.warning(
                    request,
                    "Your Seller account is currently PENDING approval from the Administrator. "
                    "You cannot upload or manage antique listings until your account is activated."
                )
                return redirect('accounts:seller_pending')

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator


def admin_required(view_func=None, raise_exception=False):
    """Restricts view to Administrator / Staff only."""
    actual_decorator = role_required(['admin'], raise_exception=raise_exception)
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


def seller_required(view_func=None, raise_exception=False, require_active=True):
    """Restricts view to registered & activated Antique Sellers only."""
    actual_decorator = role_required(
        ['seller'],
        raise_exception=raise_exception,
        require_active_seller=require_active
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


def buyer_required(view_func=None, raise_exception=False):
    """Restricts view to registered Antique Buyers only."""
    actual_decorator = role_required(['buyer'], raise_exception=raise_exception)
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator
