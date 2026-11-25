"""
Accounts views for Antique Hub.
Handles:
- Public landing page & unified common login
- Role-based redirect (Admin, Seller, Buyer)
- Buyer & Seller registrations with DFD 'Check Existing' validation
- Seller pending verification screen (DFD 'Activate Seller')
- Real-time AJAX duplicate validation endpoint
- User Profile view & edit
- Password change
- Admin seller activation management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse, NoReverseMatch
from django.db.models import Count, Q

from .forms import BuyerRegistrationForm, SellerRegistrationForm, UserProfileEditForm
from .models import UserProfile, Role
from .decorators import admin_required, seller_required, buyer_required
from catalog.models import Category, Item


def home(request):
    """
    Public landing page for Antique Hub (Module 6).
    Showcases:
    - Hero banner
    - Categories grid with live item counts
    - Featured antique artifacts (high valuation & promotional curations)
    - Latest catalog arrivals with location badges and discount badges
    """
    # Categories with live available item counts
    categories = Category.objects.annotate(
        item_count=Count('items', filter=Q(items__status='Available'))
    ).order_by('category')

    # Featured items (curated highest valuation available items)
    featured_items = Item.objects.filter(status='Available').select_related(
        'category',
        'subcategory',
        'seller',
        'seller__userprofile',
        'seller__userprofile__location',
        'seller__userprofile__district',
        'seller__userprofile__state'
    ).prefetch_related(
        'stock_records',
        'category__discounts'
    ).order_by('-price')[:4]

    # Latest arrivals
    latest_items = Item.objects.filter(status='Available').select_related(
        'category',
        'subcategory',
        'seller',
        'seller__userprofile',
        'seller__userprofile__location',
        'seller__userprofile__district',
        'seller__userprofile__state'
    ).prefetch_related(
        'stock_records',
        'category__discounts'
    ).order_by('-post_date')[:6]

    return render(request, 'home.html', {
        'categories': categories,
        'featured_items': featured_items,
        'latest_items': latest_items,
        'page_title': 'Heritage Curations & Timeless Marketplace | Antique Hub',
    })


def role_redirect(request):
    """
    Unified role-based router.
    Routes authenticated users based on assigned role and status:
    - Admin -> Custom Admin Dashboard or Django /admin/
    - Seller (Active) -> Seller Dashboard / Catalog
    - Seller (Pending) -> Seller Pending notice screen
    - Buyer -> Antique Catalog Marketplace
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    user = request.user

    # 1. Admin or Staff check
    profile = getattr(user, 'userprofile', None)
    if profile and profile.status in ['Inactive', 'Blocked']:
        messages.error(request, "Your account has been suspended or deactivated by the administrator.")
        logout(request)
        return redirect('accounts:login')

    if user.is_superuser or user.is_staff or (profile and profile.role and profile.role.role.lower() == 'admin'):
        messages.info(request, f"Welcome back, Administrator {user.username}!")
        return redirect('dashboard:admin_dashboard')

    # 2. UserProfile role check
    if profile and profile.role:
        role_name = profile.role.role.lower().strip()

        if role_name == 'seller':
            if profile.status == 'Active':
                messages.success(request, f"Welcome back, Seller {profile.contactname or user.username}!")
                try:
                    return redirect('catalog:seller_items')
                except NoReverseMatch:
                    return redirect('accounts:profile_view')
            else:
                return redirect('accounts:seller_pending')

        elif role_name == 'buyer':
            messages.success(request, f"Welcome to Antique Hub, {profile.contactname or user.username}!")
            try:
                return redirect('catalog:item_list')
            except NoReverseMatch:
                return redirect('accounts:home')

    # Fallback
    return redirect('accounts:home')


def login_view(request):
    """
    Single common login page for all roles (Admin, Seller, Buyer).
    Authenticates user and redirects via role_redirect.
    """
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                user_profile = getattr(user, 'userprofile', None)
                if user_profile and user_profile.status in ['Inactive', 'Blocked']:
                    messages.error(request, "Your account has been suspended or deactivated by the administrator.")
                    return render(request, 'accounts/login.html', {
                        'form': form,
                        'page_title': 'Unified Sign In | Antique Hub',
                    })
                login(request, user)
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('accounts:role_redirect')
        else:
            username_attempt = request.POST.get('username', '').strip()
            user_check = User.objects.filter(username=username_attempt).first()
            if user_check and (not user_check.is_active or (hasattr(user_check, 'userprofile') and user_check.userprofile.status in ['Inactive', 'Blocked'])):
                messages.error(request, "Your account has been suspended or deactivated by the administrator.")
            else:
                messages.error(request, "Invalid username or password. Please verify your credentials.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'page_title': 'Unified Sign In | Antique Hub',
    })


def logout_view(request):
    """
    Logs out user and redirects to login page with feedback.
    """
    username = request.user.username if request.user.is_authenticated else "User"
    logout(request)
    messages.success(request, f"You have been safely signed out, {username}.")
    return redirect('accounts:login')


def buyer_register(request):
    """
    Registration view for Antique Buyers.
    Buyer accounts are set to 'Active' status immediately.
    """
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            user, profile = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to Antique Hub, {profile.contactname}! Your Buyer account has been created and is active."
            )
            return redirect('accounts:role_redirect')
        else:
            messages.error(request, "Registration could not be completed. Please correct the highlighted errors.")
    else:
        form = BuyerRegistrationForm()

    return render(request, 'accounts/register_buyer.html', {
        'form': form,
        'role_title': 'Antique Collector (Buyer)',
        'page_title': 'Buyer Registration | Antique Hub',
    })


def seller_register(request):
    """
    Registration view for Antique Sellers.
    Seller accounts start with status 'Pending' awaiting Admin activation (DFD 'Activate Seller').
    """
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST)
        if form.is_valid():
            user, profile = form.save()
            login(request, user)
            messages.info(
                request,
                f"Your Seller application for '{profile.contactname}' was submitted successfully. "
                "Account status is currently PENDING Administrator verification."
            )
            return redirect('accounts:seller_pending')
        else:
            messages.error(request, "Registration could not be completed. Please correct the highlighted errors.")
    else:
        form = SellerRegistrationForm()

    return render(request, 'accounts/register_seller.html', {
        'form': form,
        'role_title': 'Antique Dealer (Seller)',
        'page_title': 'Seller Registration | Antique Hub',
    })


@login_required
def seller_pending(request):
    """
    Notice page displayed to Sellers whose account status is 'Pending'.
    Explains that listing privileges are locked until an Administrator verifies their credentials.
    """
    profile = getattr(request.user, 'userprofile', None)
    if profile and profile.status == 'Active':
        messages.success(request, "Your seller account is already activated!")
        return redirect('accounts:role_redirect')

    return render(request, 'accounts/seller_pending.html', {
        'profile': profile,
        'page_title': 'Account Verification Pending | Antique Hub',
    })


@login_required
def profile_view(request):
    """
    Displays full details of the authenticated user's profile and assigned role.
    """
    profile = getattr(request.user, 'userprofile', None)
    return render(request, 'accounts/profile_view.html', {
        'profile': profile,
        'page_title': 'My Profile | Antique Hub',
    })


@login_required
def profile_edit(request):
    """
    Form to edit contact name, phone, address, state, district, location, and email.
    """
    profile = get_object_or_404(UserProfile, login=request.user)

    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile_view')
        else:
            messages.error(request, "Could not update profile. Please check the entered data.")
    else:
        form = UserProfileEditForm(instance=profile)

    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'profile': profile,
        'page_title': 'Edit Profile | Antique Hub',
    })


@login_required
def change_password_view(request):
    """
    Allows authenticated users to change their password safely.
    Keeps session active with update_session_auth_hash.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully!")
            return redirect('accounts:profile_view')
        else:
            messages.error(request, "Please correct the password errors below.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'accounts/change_password.html', {
        'form': form,
        'page_title': 'Change Password | Antique Hub',
    })


def check_existing_ajax(request):
    """
    AJAX endpoint matching DFD step 'Check Existing'.
    Allows client-side forms to check in real-time whether a username or email is already registered.
    GET /accounts/ajax/check-existing/?field=username&value=john
    """
    field = request.GET.get('field', '').strip().lower()
    value = request.GET.get('value', '').strip()

    if not field or not value:
        return JsonResponse({'exists': False, 'message': ''})

    if field == 'username':
        exists = User.objects.filter(username__iexact=value).exists()
        message = "This username is already taken." if exists else "Username is available."
        return JsonResponse({'exists': exists, 'message': message})

    elif field == 'email':
        exists = User.objects.filter(email__iexact=value).exists()
        message = "An account with this email already exists." if exists else "Email is available."
        return JsonResponse({'exists': exists, 'message': message})

    return JsonResponse({'exists': False, 'message': 'Unknown field check.'})


# ----------------------------------------------------------------------
# Admin Seller Verification Views (Matches DFD "Activate Seller")
# ----------------------------------------------------------------------

@admin_required
def admin_seller_list(request):
    """
    Custom Admin view listing all Sellers, highlighting Pending vs Active accounts.
    Allows Administrators to audit and activate sellers directly.
    """
    pending_sellers = UserProfile.objects.filter(role__role__iexact='seller', status='Pending').select_related('login', 'state', 'district', 'location')
    active_sellers = UserProfile.objects.filter(role__role__iexact='seller', status='Active').select_related('login', 'state', 'district', 'location')

    return render(request, 'accounts/admin_seller_list.html', {
        'pending_sellers': pending_sellers,
        'active_sellers': active_sellers,
        'page_title': 'Seller Verification Console | Admin',
    })


@admin_required
def admin_activate_seller(request, user_id):
    """
    Action to activate a pending seller account.
    POST /accounts/admin/sellers/<user_id>/activate/
    """
    profile = get_object_or_404(UserProfile, userid=user_id, role__role__iexact='seller')
    profile.status = 'Active'
    profile.save()
    messages.success(request, f"Seller '{profile.contactname}' ({profile.username}) has been activated successfully!")
    return redirect('accounts:admin_seller_list')
