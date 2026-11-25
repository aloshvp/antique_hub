"""
URL configuration for the Payments app in Antique Hub (Module 8).
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Demo Sandbox Payment Checkout Flow
    path('<int:order_id>/checkout/', views.checkout_payment, name='checkout_payment'),

    # Printable Tax Invoice & Payment Receipt
    path('<int:order_id>/receipt/', views.receipt, name='receipt'),

    # Seller: View Payment and Orders (Filtered by date, status, search)
    path('seller/orders/', views.seller_payments, name='seller_payments'),

    # Admin: View Payment and Orders (Master ledger with filters)
    path('admin/orders/', views.admin_payments, name='admin_payments'),
]
