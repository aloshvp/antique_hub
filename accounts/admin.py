from django.contrib import admin
from .models import Role, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('roleid', 'role')
    search_fields = ('role',)
    ordering = ('roleid',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('userid', 'username', 'contactname', 'role', 'status', 'phone', 'email', 'regdate')
    list_filter = ('role', 'status', 'state')
    search_fields = ('username', 'contactname', 'email', 'phone')
    ordering = ('-regdate',)
    readonly_fields = ('regdate',)
