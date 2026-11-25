from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Category CRUD (Module 3)
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:cat_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:cat_id>/delete/', views.category_delete, name='category_delete'),

    # SubCategory CRUD (Module 3)
    path('subcategories/', views.subcategory_list, name='subcategory_list'),
    path('subcategories/add/', views.subcategory_add, name='subcategory_add'),
    path('subcategories/<int:subcat_id>/edit/', views.subcategory_edit, name='subcategory_edit'),
    path('subcategories/<int:subcat_id>/delete/', views.subcategory_delete, name='subcategory_delete'),

    # AJAX Cascading Endpoint
    path('ajax/load-subcategories/', views.load_subcategories_ajax, name='ajax_load_subcategories'),

    # Seller Items (Module 4)
    path('seller/items/', views.seller_item_list, name='seller_items'),
    path('seller/items/upload/', views.item_create, name='item_create'),
    path('items/<int:item_id>/edit/', views.item_update, name='item_update'),
    path('items/<int:item_id>/delete/', views.item_delete, name='item_delete'),

    # Admin Manage Items (Module 4)
    path('admin/items/', views.admin_item_list, name='admin_items'),
    path('admin/items/<int:item_id>/toggle-status/', views.admin_toggle_item_status, name='admin_toggle_item_status'),

    # Public Buyer Marketplace & Catalogue (Module 6)
    path('marketplace/', views.item_list, name='item_list'),

    # Public Item Detail Page (Module 4 & 6)
    path('items/<int:item_id>/', views.item_detail, name='item_detail'),
]
