from django.db import models
from django.contrib.auth.models import User


class Comment(models.Model):
    """
    Antique Item Review / Comment model.
    From synopsis: Comment(id, buyer FK, item FK, comments, cdate)
    
    Improvement: Added item FK (the original synopsis only had buyer id and text).
    """
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Exceptional'),
    ]

    id = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buyer_comments',
        verbose_name="Buyer / Reviewer"
    )
    item = models.ForeignKey(
        'catalog.Item',
        on_delete=models.CASCADE,
        related_name='item_comments',
        verbose_name="Antique Item"
    )
    comments = models.TextField(verbose_name="Review / Feedback Text")
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        verbose_name="Collector Rating (1 to 5 Stars)"
    )
    is_verified_buyer = models.BooleanField(
        default=False,
        help_text="Indicates if the reviewer completed purchase of this antique item",
        verbose_name="Verified Buyer"
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text="Flagged automatically or manually for inappropriate content",
        verbose_name="Flagged for Moderation"
    )
    cdate = models.DateTimeField(auto_now_add=True, verbose_name="Comment Date")
    updated_date = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        db_table = 'comment'
        ordering = ['-cdate']
        verbose_name = 'Item Comment / Review'
        verbose_name_plural = 'Item Comments / Reviews'

    def __str__(self):
        star_str = f" ({self.rating}★)" if self.rating else ""
        return f"Comment by {self.buyer.username} on '{self.item.title}'{star_str}"

    @property
    def star_range(self):
        return range(self.rating) if self.rating else []

    @property
    def empty_star_range(self):
        return range(5 - self.rating) if self.rating else []


class FAQ(models.Model):
    """
    Frequently Asked Questions on heritage curation, verification, and shipping.
    From synopsis: FAQ(faqid, faq, answer)
    """
    faqid = models.AutoField(primary_key=True)
    faq = models.CharField(max_length=255, verbose_name="Frequently Asked Question")
    answer = models.TextField(verbose_name="Detailed Answer")

    class Meta:
        db_table = 'faq'
        ordering = ['faqid']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.faq


class WatchListed(models.Model):
    """
    User Wishlist / Watchlist for antique items.
    From synopsis: WatchListed(listid, user FK, item FK, added_date)
    """
    listid = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='watchlist_items',
        verbose_name="User"
    )
    item = models.ForeignKey(
        'catalog.Item',
        on_delete=models.CASCADE,
        related_name='watchlisted_by',
        verbose_name="Antique Item"
    )
    added_date = models.DateTimeField(auto_now_add=True, verbose_name="Date Added")

    class Meta:
        db_table = 'watchlisted'
        ordering = ['-added_date']
        unique_together = ('user', 'item')
        verbose_name = 'Watchlisted Item'
        verbose_name_plural = 'Watchlisted Items'

    def __str__(self):
        return f"{self.user.username} watching '{self.item.title}'"
