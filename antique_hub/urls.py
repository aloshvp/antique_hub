"""
URL configuration for Antique Hub project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Staff Administration
    path('admin/', admin.site.urls),

    # Accounts & Authentication (also handles root '/')
    path('', include('accounts.urls')),

    # Locations & Cascading AJAX Endpoints
    path('locations/', include('locations.urls')),

    # Antique Catalog, Categories & SubCategories
    path('catalog/', include('catalog.urls')),

    # Inventory Stock Management & Control (Module 5)
    path('inventory/', include('inventory.urls')),

    # Community Reviews, FAQs & Watchlist (Module 6)
    path('community/', include('community.urls')),

    # Cart, Orders & Order Management (Module 7)
    path('orders/', include('orders.urls')),

    # Payments Gateway & Receipts (Module 8)
    path('payments/', include('payments.urls')),

    # Admin & Seller Dashboards, Analytics & Reports (Module 13)
    path('dashboard/', include('dashboard.urls')),
]

# Serve user-uploaded media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom HTTP Error Handlers (Module 14 UI)
handler404 = 'antique_hub.views.error_404'
handler403 = 'antique_hub.views.error_403'
handler500 = 'antique_hub.views.error_500'


