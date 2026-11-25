from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # 1. Main Admin Overview Console (Module 13)
    path('', views.admin_dashboard, name='admin_dashboard'),

    # 2. Manage Users (View, Search, Block / Unblock, Role Filters)
    path('users/', views.admin_users, name='admin_users'),
    path('users/<int:user_id>/toggle-status/', views.admin_user_toggle_status, name='admin_user_toggle_status'),

    # 3. Seller Activation / Deactivation Quick Actions
    path('sellers/<int:user_id>/activate/', views.admin_seller_activate, name='admin_seller_activate'),
    path('sellers/<int:user_id>/deactivate/', views.admin_seller_deactivate, name='admin_seller_deactivate'),

    # 4. Reports Hub Directory
    path('reports/', views.admin_reports_hub, name='admin_reports_hub'),

    # 5. Six Standard Audit Reports with Date Filtering & CSV/PDF Export
    path('reports/users/', views.admin_report_users, name='admin_report_users'),
    path('reports/items/', views.admin_report_items, name='admin_report_items'),
    path('reports/orders/', views.admin_report_orders, name='admin_report_orders'),
    path('reports/sales/', views.admin_report_sales, name='admin_report_sales'),
    path('reports/payments/', views.admin_report_payments, name='admin_report_payments'),
    path('reports/stock/', views.admin_report_stock, name='admin_report_stock'),
]
