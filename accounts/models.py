from django.db import models
from django.contrib.auth.models import User


class Role(models.Model):
    """
    Role master model for RBAC.
    From synopsis: Role(roleid, role)
    Standard roles: 'Admin', 'Seller', 'Buyer'
    """
    roleid = models.AutoField(primary_key=True)
    role = models.CharField(max_length=50, unique=True, verbose_name="Role Name")

    class Meta:
        db_table = 'role'
        ordering = ['role']
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return self.role


class UserProfile(models.Model):
    """
    Extended user profile linked to Django's built-in User.
    From synopsis: UserProfile(userid, username, address, state FK, district FK, 
    location FK, phone, email, regdate, status, contactname, login FK)
    
    Security Improvement: Passwords are encrypted by Django's auth User model.
    """
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Pending', 'Pending (Awaiting Admin Activation)'),
        ('Inactive', 'Inactive / Suspended'),
    ]

    userid = models.AutoField(primary_key=True)
    login = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='userprofile',
        verbose_name="Django Auth User"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='profiles',
        verbose_name="Assigned Role"
    )
    username = models.CharField(max_length=150, blank=True, verbose_name="Username")
    contactname = models.CharField(max_length=150, verbose_name="Full Contact Name")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    email = models.EmailField(max_length=254, verbose_name="Email Address")
    address = models.TextField(verbose_name="Street / Postal Address")
    
    state = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        verbose_name="State"
    )
    district = models.ForeignKey(
        'locations.District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        verbose_name="District"
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        verbose_name="Location / Ward"
    )
    regdate = models.DateTimeField(auto_now_add=True, verbose_name="Registration Date")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Active',
        verbose_name="Account Status"
    )

    class Meta:
        db_table = 'userprofile'
        ordering = ['-regdate']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.contactname} ({self.login.username}) - {self.role.role}"

    def save(self, *args, **kwargs):
        # Synchronize username with auth User
        if self.login and not self.username:
            self.username = self.login.username
        super().save(*args, **kwargs)

    @property
    def is_seller(self):
        return self.role.role.lower() == 'seller'

    @property
    def is_buyer(self):
        return self.role.role.lower() == 'buyer'

    @property
    def is_admin(self):
        return self.role.role.lower() == 'admin' or self.login.is_superuser
