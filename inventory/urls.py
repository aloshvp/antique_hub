from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Seller Stock Ledger (Module 5)
    path('seller/stock/', views.seller_stock_list, name='seller_stock'),
    path('seller/stock/<int:stock_id>/add/', views.seller_add_stock, name='seller_add_stock'),

    # Admin Stock Management (Module 5)
    path('admin/stock/', views.admin_stock_list, name='admin_stock'),
    path('admin/stock/<int:stock_id>/add/', views.admin_add_stock, name='admin_add_stock'),

    # Promotional Discounts Management & Search (Module 12)
    path('admin/discounts/', views.admin_discount_list, name='admin_discounts'),
    path('admin/discounts/add/', views.admin_discount_create, name='admin_discount_create'),
    path('admin/discounts/<int:discount_id>/edit/', views.admin_discount_update, name='admin_discount_update'),
    path('admin/discounts/<int:discount_id>/delete/', views.admin_discount_delete, name='admin_discount_delete'),
    path('discounts/search/', views.buyer_discount_search, name='discount_search'),
]
