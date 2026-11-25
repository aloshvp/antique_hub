from django.contrib import admin
from .models import Category, SubCategory, Item


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('catid', 'category', 'description')
    search_fields = ('category',)
    ordering = ('category',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('subcatid', 'subcategory', 'category')
    list_filter = ('category',)
    search_fields = ('subcategory', 'category__category')
    ordering = ('category__category', 'subcategory')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('itemid', 'item', 'title', 'category', 'price', 'years_old', 'status', 'seller', 'post_date')
    list_filter = ('category', 'status', 'post_date')
    search_fields = ('item', 'title', 'origin', 'seller__username')
    ordering = ('-post_date',)
    readonly_fields = ('post_date',)
