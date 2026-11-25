from django.contrib import admin
from .models import Comment, FAQ, WatchListed


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'item', 'rating', 'is_verified_buyer', 'is_flagged', 'cdate')
    list_filter = ('rating', 'is_verified_buyer', 'is_flagged', 'cdate')
    search_fields = ('buyer__username', 'item__title', 'comments')
    ordering = ('-cdate',)
    readonly_fields = ('cdate', 'updated_date')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('faqid', 'faq')
    search_fields = ('faq', 'answer')
    ordering = ('faqid',)


@admin.register(WatchListed)
class WatchListedAdmin(admin.ModelAdmin):
    list_display = ('listid', 'user', 'item', 'added_date')
    list_filter = ('added_date',)
    search_fields = ('user__username', 'item__title')
    ordering = ('-added_date',)
    readonly_fields = ('added_date',)
