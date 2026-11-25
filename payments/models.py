from django.db import models
from django.contrib.auth.models import User


class Payment(models.Model):
    """
    Simulated Sandbox Payment model.
    From synopsis: Payment(payid, buyer FK, purchase_master FK, amount, pay_date, method, status)
    
    Security Improvements:
    - Never stores PAN (full card number) or CVV.
    - Stores only masked last 4 digits, card brand, and simulated transaction reference.
    - Linked to PurchaseMaster with OneToOne relationship.
    """
    STATUS_CHOICES = [
        ('Success', 'Payment Successful'),
        ('Pending', 'Payment Pending Authorization'),
        ('Failed', 'Payment Failed / Declined'),
        ('Refunded', 'Payment Refunded'),
    ]

    METHOD_CHOICES = [
        ('Credit Card', 'Credit Card (Simulated Gateway)'),
        ('Debit Card', 'Debit Card (Simulated Gateway)'),
        ('Cash on Delivery', 'Cash on Delivery (COD)'),
        ('UPI', 'Unified Payments Interface (UPI Sandbox)'),
        ('Net Banking', 'Net Banking Sandbox'),
    ]

    payid = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buyer_payments',
        verbose_name="Buyer"
    )
    purchase_master = models.OneToOneField(
        'orders.PurchaseMaster',
        on_delete=models.CASCADE,
        related_name='payment_record',
        verbose_name="Order Reference"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Amount Paid (INR)"
    )
    pay_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Payment Timestamp"
    )
    method = models.CharField(
        max_length=50,
        choices=METHOD_CHOICES,
        default='Credit Card',
        verbose_name="Payment Method"
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='Success',
        verbose_name="Payment Status"
    )
    card_last4 = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="Masked card number: only last 4 digits stored for PCI-DSS compliance",
        verbose_name="Card Last 4 Digits"
    )
    card_type = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Detected card network (e.g. Visa, MasterCard, RuPay, Amex)",
        verbose_name="Card Type / Network"
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Issuing bank or financial institution (e.g. State Bank of India, HDFC, ICICI)",
        verbose_name="Bank Name"
    )
    transaction_ref = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique gateway transaction reference id (e.g. TXN-AH-84920492)",
        verbose_name="Transaction Reference"
    )

    class Meta:
        db_table = 'payment'
        ordering = ['-pay_date']
        verbose_name = 'Payment Record'
        verbose_name_plural = 'Payment Records'

    def __str__(self):
        return f"Payment #{self.payid} (₹{self.amount} - {self.status}) [Ref: {self.transaction_ref}]"
