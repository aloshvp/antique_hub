from django.db import models, transaction
from django.utils import timezone


class InsufficientStockError(Exception):
    """
    Raised when attempting to reduce more stock than available in inventory.
    Used during order confirmation to prevent overselling.
    """
    pass


class Stock(models.Model):
    """
    Inventory stock ledger model.
    From synopsis: Stock(stockid, item FK, tot_arr_stock, cur_stock, stockdate, status)
    
    Business Rules (Module 5):
    - Low-stock threshold warning at 2 or fewer units (0 < cur_stock <= 2).
    - Automatically transitions to 'Out of Stock' when cur_stock hits 0.
    - Automatically restores item status to 'Available' when restocked.
    - Transactional row-locking reduction via reduce_stock() using select_for_update().
    """
    LOW_STOCK_THRESHOLD = 2

    stockid = models.AutoField(primary_key=True)
    item = models.ForeignKey(
        'catalog.Item',
        on_delete=models.CASCADE,
        related_name='stock_records',
        verbose_name="Antique Item"
    )
    tot_arr_stock = models.PositiveIntegerField(
        default=0,
        verbose_name="Total Arrived Stock"
    )
    cur_stock = models.PositiveIntegerField(
        default=0,
        verbose_name="Current Available Stock"
    )
    stockdate = models.DateTimeField(
        default=timezone.now,
        verbose_name="Stock Updated Date"
    )
    status = models.CharField(
        max_length=50,
        default='In Stock',
        verbose_name="Stock Status"
    )

    class Meta:
        db_table = 'stock'
        ordering = ['-stockdate']
        verbose_name = 'Inventory Stock'
        verbose_name_plural = 'Inventory Stocks'

    def __str__(self):
        return f"Stock for {self.item.title} (Available: {self.cur_stock}/{self.tot_arr_stock})"

    @property
    def is_low_stock(self):
        """Returns True if stock is within the low stock warning threshold (1 or 2 units)."""
        return 0 < self.cur_stock <= self.LOW_STOCK_THRESHOLD

    @property
    def is_out_of_stock(self):
        """Returns True if available units have hit 0."""
        return self.cur_stock == 0

    def save(self, *args, **kwargs):
        """
        Synchronize stock status and item status automatically:
        - If cur_stock == 0: stock status = 'Out of Stock', item status = 'Out of Stock' (if Available)
        - If cur_stock > 0: stock status = 'In Stock', item status = 'Available' (if Out of Stock)
        """
        if self.cur_stock <= 0:
            self.status = 'Out of Stock'
        else:
            self.status = 'In Stock'
        super().save(*args, **kwargs)

        # Synchronize linked item status (preserve intentional 'Hidden' status)
        if hasattr(self, 'item') and self.item_id:
            item = self.item
            if self.cur_stock <= 0 and item.status == 'Available':
                item.status = 'Out of Stock'
                item.save(update_fields=['status'])
            elif self.cur_stock > 0 and item.status == 'Out of Stock':
                item.status = 'Available'
                item.save(update_fields=['status'])

    @transaction.atomic
    def add_stock(self, quantity):
        """
        Restock antique artifact:
        Increases tot_arr_stock and cur_stock, logs stockdate, and updates status.
        """
        if quantity <= 0:
            raise ValueError("Quantity to add must be greater than zero.")

        self.tot_arr_stock += quantity
        self.cur_stock += quantity
        self.stockdate = timezone.now()
        self.save()
        return self

    @classmethod
    @transaction.atomic
    def reduce_stock(cls, item_id, quantity):
        """
        Atomic row-locking stock reduction (DFD 3.1 & 3.2):
        Stock must be reduced ONLY when an order is confirmed, using select_for_update()
        to guarantee row-level locking and prevent overselling during concurrent checkouts.
        """
        if quantity <= 0:
            raise ValueError("Quantity to reduce must be greater than zero.")

        # Lock the row in DB
        stock = cls.objects.select_for_update().select_related('item').get(item_id=item_id)

        if stock.cur_stock < quantity:
            raise InsufficientStockError(
                f"Insufficient stock for '{stock.item.title}'. Requested: {quantity}, Available: {stock.cur_stock}."
            )

        stock.cur_stock -= quantity
        stock.stockdate = timezone.now()
        stock.save()
        return stock


class Discount(models.Model):
    """
    Promotional discounts applicable to antique categories (or all categories).
    From synopsis: Discount(discountid, applicable_cat, discount_percent, startdate, enddate)
    """
    discountid = models.AutoField(primary_key=True)
    applicable_cat = models.ForeignKey(
        'catalog.Category',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name="Applicable Category (Leave empty for All Categories)"
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage discount (1 to 90), e.g. 15.00 for 15%",
        verbose_name="Discount Percent (%)"
    )
    startdate = models.DateField(verbose_name="Start Date")
    enddate = models.DateField(verbose_name="End Date")

    class Meta:
        db_table = 'discount'
        ordering = ['-startdate']
        verbose_name = 'Category Discount'
        verbose_name_plural = 'Category Discounts'

    def __str__(self):
        cat_name = self.applicable_cat.category if self.applicable_cat else "All Categories"
        return f"{self.discount_percent}% off on {cat_name} ({self.startdate} to {self.enddate})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.startdate and self.enddate and self.enddate <= self.startdate:
            raise ValidationError({
                'enddate': "End date must be strictly after the start date."
            })
        if self.discount_percent is not None:
            if self.discount_percent < 1 or self.discount_percent > 90:
                raise ValidationError({
                    'discount_percent': "Discount percent must be between 1% and 90%."
                })

    @property
    def is_active(self):
        today = timezone.localdate()
        return self.startdate <= today <= self.enddate

    @property
    def is_expired(self):
        today = timezone.localdate()
        return self.enddate < today

    @property
    def is_upcoming(self):
        today = timezone.localdate()
        return self.startdate > today

    @property
    def status_label(self):
        if self.is_active:
            return 'Active'
        elif self.is_upcoming:
            return 'Upcoming'
        return 'Expired'

