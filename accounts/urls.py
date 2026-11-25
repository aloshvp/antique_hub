from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Core Landing & Auth
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.role_redirect, name='role_redirect'),

    # Registration Portals
    path('register/buyer/', views.buyer_register, name='buyer_register'),
    path('register/seller/', views.seller_register, name='seller_register'),
    path('seller-pending/', views.seller_pending, name='seller_pending'),

    # User Profile & Security
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('password-change/', views.change_password_view, name='change_password'),

    # Real-time AJAX Check Existing (DFD Step)
    path('ajax/check-existing/', views.check_existing_ajax, name='ajax_check_existing'),

    # Admin Seller Activation Management (DFD Step "Activate Seller")
    path('admin-portal/sellers/', views.admin_seller_list, name='admin_seller_list'),
    path('admin-portal/sellers/<int:user_id>/activate/', views.admin_activate_seller, name='admin_activate_seller'),
]
