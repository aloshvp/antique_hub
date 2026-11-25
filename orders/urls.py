from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # 1. Cart Operations (Module 7)
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/<int:cart_id>/update/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/<int:cart_id>/remove/', views.remove_from_cart, name='remove_from_cart'),

    # 2. Checkout & Order Placement (Atomic Transaction & Row Locking - DFD 1.3, 1.3.1)
    path('checkout/confirm/', views.confirm_order, name='confirm_order'),

    # 3. Buyer Orders & Tracking
    path('my-orders/', views.buyer_orders, name='buyer_orders'),
    path('<int:purchase_id>/', views.order_detail, name='order_detail'),
    path('<int:purchase_id>/cancel/', views.cancel_order, name='cancel_order'),

    # 4. Seller Orders View
    path('seller/', views.seller_orders, name='seller_orders'),

    # 5. Admin Master Order Management (DFD 5.1 to 5.3)
    path('admin/', views.admin_orders, name='admin_orders'),
    path('admin/<int:purchase_id>/status/', views.admin_update_status, name='admin_update_status'),
]
