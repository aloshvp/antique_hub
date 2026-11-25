from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class Cart(models.Model):
    """
    Shopping cart item for an authenticated buyer.
    From synopsis: cart(cartid, buyer FK, item FK, quantity, added_date)
    """
    cartid = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name="Buyer"
    )
    item = models.ForeignKey(
        'catalog.Item',
        on_delete=models.CASCADE,
        related_name='in_carts',
        verbose_name="Antique Item"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantity"
    )
    added_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date Added"
    )

    class Meta:
        db_table = 'cart'
        unique_together = ('buyer', 'item')
        ordering = ['-added_date']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'

    def __str__(self):
        return f"{self.quantity}x '{self.item.title}' in {self.buyer.username}'s Cart"

    @property
    def unit_price(self):
        return self.item.discounted_price

    @property
    def original_unit_price(self):
        return self.item.price

    @property
    def subtotal(self):
        return round(self.unit_price * self.quantity, 2)

    @property
    def original_subtotal(self):
        return round(self.original_unit_price * self.quantity, 2)

    @property
    def discount_saved(self):
        return round(self.original_subtotal - self.subtotal, 2)


class PurchaseMaster(models.Model):
    """
    Master record for an antique order.
    From synopsis: PurchaseMaster(purchaseid, buyer FK, purdate, ship_charge, tot_amt, status, pay_status)
    """
    STATUS_CHOICES = [
        ('Pending', 'Order Placed (Pending)'),
        ('Confirmed', 'Order Confirmed'),
        ('Shipped', 'Shipped via Heritage Courier'),
        ('Delivered', 'Delivered to Buyer'),
        ('Cancelled', 'Cancelled'),
    ]

    PAY_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Pending', 'Pending Payment'),
        ('Paid', 'Payment Completed'),
        ('Failed', 'Payment Failed'),
        ('Refunded', 'Payment Refunded'),
    ]

    purchaseid = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buyer_orders',
        verbose_name="Buyer"
    )
    purdate = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Order Date"
    )
    ship_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Shipping Charge (INR)"
    )
    tot_amt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Order Amount (INR)"
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name="Order Fulfillment Status"
    )
    pay_status = models.CharField(
        max_length=30,
        choices=PAY_STATUS_CHOICES,
        default='Pending',
        verbose_name="Payment Status"
    )

    class Meta:
        db_table = 'purchase_master'
        ordering = ['-purdate']
        verbose_name = 'Purchase Master'
        verbose_name_plural = 'Purchase Masters'

    def __str__(self):
        return f"Order #{self.purchaseid} by {self.buyer.username} - ₹{self.tot_amt} ({self.status})"

    @property
    def items_total(self):
        """Calculates total of line items using their snapshotted prices."""
        return sum((p.subtotal for p in self.order_items.all()), Decimal('0.00'))



class Purchase(models.Model):
    """
    Individual item line in a purchase order.
    From synopsis: Purchase(pid, purchase_master FK, item FK, quantity)
    """
    pid = models.AutoField(primary_key=True)
    purchase_master = models.ForeignKey(
        PurchaseMaster,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name="Purchase Master Reference"
    )
    item = models.ForeignKey(
        'catalog.Item',
        on_delete=models.CASCADE,
        related_name='purchases',
        verbose_name="Antique Item"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantity Ordered"
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Price Paid per Unit (INR)"
    )

    class Meta:
        db_table = 'purchase'
        ordering = ['pid']
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.quantity}x {self.item.title} (Order #{self.purchase_master.purchaseid}) @ ₹{self.price}"

    def save(self, *args, **kwargs):
        """
        Module 12: Snapshot the effective price paid per unit at the moment of order placement.
        Ensures subsequent price or discount modifications do not alter old historical orders.
        """
        if (self.price is None or self.price == 0) and hasattr(self, 'item') and self.item_id:
            self.price = self.item.discounted_price
        super().save(*args, **kwargs)

    @property
    def unit_price(self):
        """Returns the snapshotted price paid per unit."""
        return self.price

    @property
    def subtotal(self):
        """Returns the total price paid for this line item (snapshotted price * quantity)."""
        return round(self.price * self.quantity, 2)
