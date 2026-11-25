from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    # State CRUD (DFD 1.1.1)
    path('states/', views.state_list, name='state_list'),
    path('states/add/', views.state_add, name='state_add'),
    path('states/<int:state_id>/edit/', views.state_edit, name='state_edit'),
    path('states/<int:state_id>/delete/', views.state_delete, name='state_delete'),

    # District CRUD (DFD 1.1.2)
    path('districts/', views.district_list, name='district_list'),
    path('districts/add/', views.district_add, name='district_add'),
    path('districts/<int:dist_id>/edit/', views.district_edit, name='district_edit'),
    path('districts/<int:dist_id>/delete/', views.district_delete, name='district_delete'),

    # Location CRUD (DFD 1.1.3)
    path('', views.location_list, name='location_list'),
    path('add/', views.location_add, name='location_add'),
    path('<int:loc_id>/edit/', views.location_edit, name='location_edit'),
    path('<int:loc_id>/delete/', views.location_delete, name='location_delete'),

    # JSON Endpoints for Cascading Dropdowns
    path('ajax/load-districts/', views.load_districts, name='ajax_load_districts'),
    path('ajax/load-locations/', views.load_locations, name='ajax_load_locations'),
]
