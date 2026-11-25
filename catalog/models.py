from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """
    Main Antique Category model.
    From synopsis: Category(catid, category)
    E.g., Furniture, Decor, Coins, Jewellery, Artefacts, Collectibles
    """
    catid = models.AutoField(primary_key=True)
    category = models.CharField(max_length=100, unique=True, verbose_name="Category Name")
    description = models.TextField(blank=True, verbose_name="Category Description")

    class Meta:
        db_table = 'category'
        ordering = ['category']
        verbose_name = 'Antique Category'
        verbose_name_plural = 'Antique Categories'

    def __str__(self):
        return self.category


class SubCategory(models.Model):
    """
    Subcategory linked to Category.
    From synopsis: SubCategory(subcatid, subcategory, category FK)
    """
    subcatid = models.AutoField(primary_key=True)
    subcategory = models.CharField(max_length=100, verbose_name="SubCategory Name")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="Category"
    )

    class Meta:
        db_table = 'subcategory'
        ordering = ['category__category', 'subcategory']
        unique_together = ('category', 'subcategory')
        verbose_name = 'Antique SubCategory'
        verbose_name_plural = 'Antique SubCategories'

    def __str__(self):
        return f"{self.subcategory} ({self.category.category})"


class Item(models.Model):
    """
    Antique Item listing model.
    From synopsis: Item(itemid, item, title, category FK, subcategory FK, 
    years_old, origin, post_date, description, img1, img2, price, status, seller FK)
    
    Improvements:
    - Uses ImageField with media upload instead of flat path strings.
    - Expanded title & TextField description for rich historical provenance.
    - Strict FK constraints, indexes on status and post_date.
    """
    STATUS_CHOICES = [
        ('Available', 'Available for Purchase'),
        ('Out of Stock', 'Out of Stock'),
        ('Hidden', 'Hidden from Marketplace'),
        ('Sold', 'Sold Out'),
    ]

    itemid = models.AutoField(primary_key=True)
    item = models.CharField(
        max_length=100,
        help_text="Item code or SKU identifier (e.g. ANT-1890-CHAIR)",
        verbose_name="Item Code / Reference"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Antique Title"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Category"
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        verbose_name="SubCategory"
    )
    years_old = models.PositiveIntegerField(
        help_text="Approximate age of the item in years",
        verbose_name="Age (Years Old)"
    )
    origin = models.CharField(
        max_length=150,
        help_text="Geographical or cultural origin (e.g. Mughal Empire, India; Victorian Britain)",
        verbose_name="Origin / Provenance"
    )
    post_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Listing Date"
    )
    description = models.TextField(
        verbose_name="Historical Description & Condition Details"
    )
    img1 = models.ImageField(
        upload_to='antiques/items/',
        verbose_name="Primary Antique Photograph"
    )
    img2 = models.ImageField(
        upload_to='antiques/items/',
        blank=True,
        null=True,
        verbose_name="Secondary / Hallmark Photograph"
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Price (INR)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Available',
        db_index=True,
        verbose_name="Listing Status"
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='antique_items',
        verbose_name="Seller"
    )

    class Meta:
        db_table = 'item'
        ordering = ['-post_date']
        indexes = [
            models.Index(fields=['status', 'post_date']),
            models.Index(fields=['category', 'status']),
        ]
        verbose_name = 'Antique Item'
        verbose_name_plural = 'Antique Items'

    def __str__(self):
        return f"{self.title} (Code: {self.item}) - ₹{self.price}"

    @property
    def current_stock(self):
        latest_stock = self.stock_records.first()
        return latest_stock.cur_stock if latest_stock else 0

    @property
    def active_discount(self):
        """Returns the active Discount object via centralized pricing helper."""
        from inventory.utils import get_effective_price
        return get_effective_price(self)['active_discount']

    @property
    def has_discount(self):
        """Returns True if an active promotional discount currently applies."""
        from inventory.utils import get_effective_price
        return get_effective_price(self)['has_discount']

    @property
    def discounted_price(self):
        """Returns the calculated effective price (discounted or original) via centralized helper."""
        from inventory.utils import get_effective_price
        return get_effective_price(self)['effective_price']

    @property
    def discount_percent(self):
        """Returns the active discount percentage (e.g. 15.00) or 0."""
        from inventory.utils import get_effective_price
        return get_effective_price(self)['discount_percent']

