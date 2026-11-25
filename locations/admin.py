from django.contrib import admin
from .models import State, District, Location


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('stateid', 'state')
    search_fields = ('state',)
    ordering = ('state',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('distid', 'dist', 'state')
    list_filter = ('state',)
    search_fields = ('dist', 'state__state')
    ordering = ('state__state', 'dist')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('locid', 'locname', 'get_district', 'get_state')
    list_filter = ('district__state',)
    search_fields = ('locname', 'district__dist', 'district__state__state')
    ordering = ('district__state__state', 'district__dist', 'locname')

    @admin.display(description='District', ordering='district__dist')
    def get_district(self, obj):
        return obj.district.dist

    @admin.display(description='State', ordering='district__state__state')
    def get_state(self, obj):
        return obj.district.state.state
