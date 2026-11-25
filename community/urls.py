"""
URL routing for Community Module (Module 9 - Comments, Reviews, Moderation, and Watchlist).
"""

from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Comment Submission (Item detail page)
    path('items/<int:item_id>/comment/', views.add_comment, name='add_comment'),

    # Comment Author Actions (Edit & Delete)
    path('comments/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Seller: View Comments on their own items
    path('seller/comments/', views.seller_comments, name='seller_comments'),

    # Admin: Moderation Console for Comments & Reviews
    path('admin/comments/', views.admin_comments, name='admin_comments'),
    path('admin/comments/<int:comment_id>/delete/', views.admin_delete_comment, name='admin_delete_comment'),

    # Watchlist Management & DFD 3.0 Report
    path('watchlist/', views.watchlist_view, name='watchlist_view'),
    path('watchlist/<int:item_id>/move-to-cart/', views.move_to_cart, name='move_to_cart'),
    path('items/<int:item_id>/watchlist/toggle/', views.toggle_watchlist, name='toggle_watchlist'),
    path('admin/watchlist/', views.admin_watchlist, name='admin_watchlist'),

    # Frequently Asked Questions (Module 11) & Collector Policies
    path('faq/', views.faq_view, name='faq_view'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('admin/faq/', views.admin_faq_list, name='admin_faq_list'),
    path('admin/faq/add/', views.admin_faq_create, name='admin_faq_create'),
    path('admin/faq/<int:faqid>/edit/', views.admin_faq_update, name='admin_faq_update'),
    path('admin/faq/<int:faqid>/delete/', views.admin_faq_delete, name='admin_faq_delete'),
]

