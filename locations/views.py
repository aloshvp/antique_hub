"""
Locations views for Antique Hub.
Implements Admin-only CRUD for:
- State (DFD 1.1.1)
- District (DFD 1.1.2)
- Location (DFD 1.1.3)
with search, pagination, and child-record deletion protection.
Also includes JSON endpoints for cascading registration dropdowns.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse

from accounts.decorators import admin_required
from .models import State, District, Location
from .forms import StateForm, DistrictForm, LocationForm


# ======================================================================
# 1. State CRUD (DFD 1.1.1)
# ======================================================================

@admin_required
def state_list(request):
    """
    Admin view listing all states with search, pagination, and district count.
    """
    query = request.GET.get('q', '').strip()
    states_qs = State.objects.annotate(districts_count=Count('districts')).order_by('state')

    if query:
        states_qs = states_qs.filter(state__icontains=query)

    paginator = Paginator(states_qs, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'locations/state_list.html', {
        'page_obj': page_obj,
        'query': query,
        'page_title': 'State Master | Admin Console',
    })


@admin_required
def state_add(request):
    """
    Add a new State.
    """
    if request.method == 'POST':
        form = StateForm(request.POST)
        if form.is_valid():
            state = form.save()
            messages.success(request, f"State '{state.state}' added successfully.")
            return redirect('locations:state_list')
        else:
            messages.error(request, "Failed to add state. Please correct the error below.")
    else:
        form = StateForm()

    return render(request, 'locations/state_form.html', {
        'form': form,
        'action_title': 'Add New State',
        'page_title': 'Add State | Admin',
    })


@admin_required
def state_edit(request, state_id):
    """
    Edit an existing State.
    """
    state = get_object_or_404(State, stateid=state_id)

    if request.method == 'POST':
        form = StateForm(request.POST, instance=state)
        if form.is_valid():
            state = form.save()
            messages.success(request, f"State '{state.state}' updated successfully.")
            return redirect('locations:state_list')
        else:
            messages.error(request, "Failed to update state. Please correct the error below.")
    else:
        form = StateForm(instance=state)

    return render(request, 'locations/state_form.html', {
        'form': form,
        'state': state,
        'action_title': f"Edit State: {state.state}",
        'page_title': f"Edit State: {state.state} | Admin",
    })


@admin_required
def state_delete(request, state_id):
    """
    Delete confirmation and action for State.
    Blocks deletion if child districts exist!
    """
    state = get_object_or_404(State, stateid=state_id)
    child_districts_count = state.districts.count()
    child_profiles_count = state.user_profiles.count()

    if request.method == 'POST':
        # Block deletion if child records exist
        if child_districts_count > 0:
            messages.error(
                request,
                f"Cannot delete State '{state.state}' because it contains {child_districts_count} "
                "associated district(s). Please delete or reassign all child districts first."
            )
            return redirect('locations:state_list')

        if child_profiles_count > 0:
            messages.error(
                request,
                f"Cannot delete State '{state.state}' because it is linked to {child_profiles_count} user profile(s)."
            )
            return redirect('locations:state_list')

        state_name = state.state
        state.delete()
        messages.success(request, f"State '{state_name}' deleted successfully.")
        return redirect('locations:state_list')

    return render(request, 'locations/state_confirm_delete.html', {
        'state': state,
        'child_districts_count': child_districts_count,
        'child_profiles_count': child_profiles_count,
        'page_title': f"Confirm Deletion: {state.state} | Admin",
    })


# ======================================================================
# 2. District CRUD (DFD 1.1.2)
# ======================================================================

@admin_required
def district_list(request):
    """
    Admin view listing all districts with state filter, search, pagination, and location count.
    """
    query = request.GET.get('q', '').strip()
    state_id = request.GET.get('state_id', '').strip()

    districts_qs = District.objects.select_related('state').annotate(
        locations_count=Count('locations')
    ).order_by('state__state', 'dist')

    if state_id:
        districts_qs = districts_qs.filter(state_id=state_id)

    if query:
        districts_qs = districts_qs.filter(
            Q(dist__icontains=query) | Q(state__state__icontains=query)
        )

    states = State.objects.all().order_by('state')
    paginator = Paginator(districts_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'locations/district_list.html', {
        'page_obj': page_obj,
        'states': states,
        'selected_state_id': state_id,
        'query': query,
        'page_title': 'District Master | Admin Console',
    })


@admin_required
def district_add(request):
    """
    Add a new District (needs a state).
    """
    initial = {}
    state_id = request.GET.get('state_id')
    if state_id:
        initial['state'] = state_id

    if request.method == 'POST':
        form = DistrictForm(request.POST)
        if form.is_valid():
            district = form.save()
            messages.success(request, f"District '{district.dist}' added successfully under '{district.state.state}'.")
            return redirect('locations:district_list')
        else:
            messages.error(request, "Failed to add district. Please check the errors below.")
    else:
        form = DistrictForm(initial=initial)

    return render(request, 'locations/district_form.html', {
        'form': form,
        'action_title': 'Add New District',
        'page_title': 'Add District | Admin',
    })


@admin_required
def district_edit(request, dist_id):
    """
    Edit an existing District.
    """
    district = get_object_or_404(District, distid=dist_id)

    if request.method == 'POST':
        form = DistrictForm(request.POST, instance=district)
        if form.is_valid():
            district = form.save()
            messages.success(request, f"District '{district.dist}' updated successfully.")
            return redirect('locations:district_list')
        else:
            messages.error(request, "Failed to update district. Please check the errors below.")
    else:
        form = DistrictForm(instance=district)

    return render(request, 'locations/district_form.html', {
        'form': form,
        'district': district,
        'action_title': f"Edit District: {district.dist}",
        'page_title': f"Edit District: {district.dist} | Admin",
    })


@admin_required
def district_delete(request, dist_id):
    """
    Delete confirmation and action for District.
    Blocks deletion if child locations exist!
    """
    district = get_object_or_404(District, distid=dist_id)
    child_locations_count = district.locations.count()
    child_profiles_count = district.user_profiles.count()

    if request.method == 'POST':
        # Block deletion if child records exist
        if child_locations_count > 0:
            messages.error(
                request,
                f"Cannot delete District '{district.dist}' because it contains {child_locations_count} "
                "associated location(s). Please delete or reassign all child locations first."
            )
            return redirect('locations:district_list')

        if child_profiles_count > 0:
            messages.error(
                request,
                f"Cannot delete District '{district.dist}' because it is linked to {child_profiles_count} user profile(s)."
            )
            return redirect('locations:district_list')

        dist_name = district.dist
        district.delete()
        messages.success(request, f"District '{dist_name}' deleted successfully.")
        return redirect('locations:district_list')

    return render(request, 'locations/district_confirm_delete.html', {
        'district': district,
        'child_locations_count': child_locations_count,
        'child_profiles_count': child_profiles_count,
        'page_title': f"Confirm Deletion: {district.dist} | Admin",
    })


# ======================================================================
# 3. Location CRUD (DFD 1.1.3)
# ======================================================================

@admin_required
def location_list(request):
    """
    Admin view listing all locations with district/state filter, search, pagination, and linked profiles count.
    """
    query = request.GET.get('q', '').strip()
    district_id = request.GET.get('district_id', '').strip()

    locations_qs = Location.objects.select_related('district', 'district__state').annotate(
        profiles_count=Count('user_profiles')
    ).order_by('district__state__state', 'district__dist', 'locname')

    if district_id:
        locations_qs = locations_qs.filter(district_id=district_id)

    if query:
        locations_qs = locations_qs.filter(
            Q(locname__icontains=query) |
            Q(district__dist__icontains=query) |
            Q(district__state__state__icontains=query)
        )

    districts = District.objects.select_related('state').order_by('state__state', 'dist')
    paginator = Paginator(locations_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'locations/location_list.html', {
        'page_obj': page_obj,
        'districts': districts,
        'selected_district_id': district_id,
        'query': query,
        'page_title': 'Location Master | Admin Console',
    })


@admin_required
def location_add(request):
    """
    Add a new Location (needs a district).
    """
    initial = {}
    district_id = request.GET.get('district_id')
    if district_id:
        try:
            d = District.objects.get(pk=district_id)
            initial['district'] = d.pk
            initial['state'] = d.state.pk
        except District.DoesNotExist:
            pass

    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save()
            messages.success(
                request,
                f"Location '{location.locname}' added successfully under '{location.district.dist}' ({location.district.state.state})."
            )
            return redirect('locations:location_list')
        else:
            messages.error(request, "Failed to add location. Please check the errors below.")
    else:
        form = LocationForm(initial=initial)

    return render(request, 'locations/location_form.html', {
        'form': form,
        'action_title': 'Add New Location',
        'page_title': 'Add Location | Admin',
    })


@admin_required
def location_edit(request, loc_id):
    """
    Edit an existing Location.
    """
    location = get_object_or_404(Location, locid=loc_id)

    if request.method == 'POST':
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            location = form.save()
            messages.success(request, f"Location '{location.locname}' updated successfully.")
            return redirect('locations:location_list')
        else:
            messages.error(request, "Failed to update location. Please check the errors below.")
    else:
        form = LocationForm(instance=location)

    return render(request, 'locations/location_form.html', {
        'form': form,
        'location': location,
        'action_title': f"Edit Location: {location.locname}",
        'page_title': f"Edit Location: {location.locname} | Admin",
    })


@admin_required
def location_delete(request, loc_id):
    """
    Delete confirmation and action for Location.
    Blocks deletion if linked to registered user profiles!
    """
    location = get_object_or_404(Location, locid=loc_id)
    child_profiles_count = location.user_profiles.count()

    if request.method == 'POST':
        # Block deletion if linked to users
        if child_profiles_count > 0:
            messages.error(
                request,
                f"Cannot delete Location '{location.locname}' because it is linked to {child_profiles_count} "
                "registered user profile(s)."
            )
            return redirect('locations:location_list')

        loc_name = location.locname
        location.delete()
        messages.success(request, f"Location '{loc_name}' deleted successfully.")
        return redirect('locations:location_list')

    return render(request, 'locations/location_confirm_delete.html', {
        'location': location,
        'child_profiles_count': child_profiles_count,
        'page_title': f"Confirm Deletion: {location.locname} | Admin",
    })


# ======================================================================
# 4. JSON Endpoints for Cascading Dropdowns
# ======================================================================

def load_districts(request):
    """
    AJAX JSON endpoint to return districts for a selected state.
    Used by registration, profile edit, and location add forms.
    GET /locations/ajax/load-districts/?state_id=1
    """
    state_id = request.GET.get('state_id')
    if not state_id:
        return JsonResponse({'districts': []})

    districts = District.objects.filter(state_id=state_id).order_by('dist').values('distid', 'dist')
    return JsonResponse({'districts': list(districts)})


def load_locations(request):
    """
    AJAX JSON endpoint to return locations for a selected district.
    Used by registration and profile edit forms.
    GET /locations/ajax/load-locations/?district_id=1
    """
    district_id = request.GET.get('district_id')
    if not district_id:
        return JsonResponse({'locations': []})

    locations = Location.objects.filter(district_id=district_id).order_by('locname').values('locid', 'locname')
    return JsonResponse({'locations': list(locations)})
