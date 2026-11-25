"""
Forms for Accounts app in Antique Hub.
Handles:
- Buyer & Seller registration with DFD 'Check Existing' validation
- Indian 10-digit phone regex validation
- Password strength & confirmation
- Dynamic cascading state -> district -> location population
- UserProfile editing
"""

import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Role, UserProfile
from locations.models import State, District, Location


INDIAN_PHONE_REGEX = re.compile(r'^[6-9]\d{9}$')


class BaseRegistrationForm(forms.Form):
    """
    Base registration form defining common fields, validations, and cascading dropdown logic.
    """
    contactname = forms.CharField(
        max_length=150,
        label="Full Contact Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Rajesh Kumar'}),
    )
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a unique username'}),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
    )
    phone = forms.CharField(
        max_length=15,
        label="Phone Number (Indian 10-digit)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
    )
    address = forms.CharField(
        label="Street / Postal Address",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter your street address, building/door no.'}),
    )
    state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        empty_label="-- Select State --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_state'}),
    )
    district = forms.ModelChoiceField(
        queryset=District.objects.none(),
        empty_label="-- Select District --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_district'}),
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        empty_label="-- Select Location --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_location'}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min 8 chars, letters & numbers'}),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat your password'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamic queryset population on POST or re-render
        if 'state' in self.data:
            try:
                state_id = int(self.data.get('state'))
                self.fields['district'].queryset = District.objects.filter(state_id=state_id).order_by('dist')
            except (ValueError, TypeError):
                pass

        if 'district' in self.data:
            try:
                district_id = int(self.data.get('district'))
                self.fields['location'].queryset = Location.objects.filter(district_id=district_id).order_by('locname')
            except (ValueError, TypeError):
                pass

    def clean_username(self):
        """
        DFD Step: 'Check Existing'
        Ensures username is unique across all user records (case-insensitive).
        """
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username may only contain letters, numbers, and underscores.")

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another username.")
        return username

    def clean_email(self):
        """
        DFD Step: 'Check Existing'
        Ensures email is unique across all user records (case-insensitive).
        """
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address is already registered.")
        return email

    def clean_phone(self):
        """
        Validates 10-digit Indian mobile number format (starts with 6, 7, 8, or 9).
        """
        phone = self.cleaned_data.get('phone', '').strip().replace(' ', '').replace('-', '')
        if not INDIAN_PHONE_REGEX.match(phone):
            raise ValidationError("Please enter a valid 10-digit Indian phone number starting with 6, 7, 8, or 9.")
        return phone

    def clean_password(self):
        """
        Validates password strength: at least 8 characters, containing both letters and numbers.
        """
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            raise ValidationError("Password must include at least one letter and at least one number.")
        return password

    def clean(self):
        """
        Validates that password and confirm_password match.
        """
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match. Please re-enter carefully.")
        return cleaned_data

    def save_user(self, role_name, status):
        """
        Creates auth.User with encrypted password and attached UserProfile with assigned role and status.
        """
        cd = self.cleaned_data
        # 1. Create Django User
        user = User.objects.create_user(
            username=cd['username'],
            email=cd['email'],
            password=cd['password'],
            first_name=cd['contactname'],
        )

        # 2. Get Role
        role_obj, _ = Role.objects.get_or_create(role=role_name)

        # 3. Create UserProfile
        profile = UserProfile.objects.create(
            login=user,
            role=role_obj,
            username=cd['username'],
            contactname=cd['contactname'],
            phone=cd['phone'],
            email=cd['email'],
            address=cd['address'],
            state=cd.get('state'),
            district=cd.get('district'),
            location=cd.get('location'),
            status=status,
        )
        return user, profile


class BuyerRegistrationForm(BaseRegistrationForm):
    """
    Registration form for antique buyers.
    Account status is 'Active' immediately upon registration.
    """
    def save(self):
        return self.save_user(role_name='Buyer', status='Active')


class SellerRegistrationForm(BaseRegistrationForm):
    """
    Registration form for antique sellers.
    Account status is 'Pending' awaiting Admin verification (matches DFD 'Activate Seller').
    """
    business_license = forms.CharField(
        max_length=100,
        required=False,
        label="Antique Dealer Registration / GST (Optional)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dealer Reg. / Trade ID'}),
    )

    def save(self):
        return self.save_user(role_name='Seller', status='Pending')


class UserProfileEditForm(forms.ModelForm):
    """
    Form for editing user profile details (contactname, phone, address, state, district, location, email).
    """
    class Meta:
        model = UserProfile
        fields = ['contactname', 'email', 'phone', 'address', 'state', 'district', 'location']
        widgets = {
            'contactname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.Select(attrs={'class': 'form-select', 'id': 'id_state'}),
            'district': forms.Select(attrs={'class': 'form-select', 'id': 'id_district'}),
            'location': forms.Select(attrs={'class': 'form-select', 'id': 'id_location'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.state:
                self.fields['district'].queryset = District.objects.filter(state=self.instance.state).order_by('dist')
            if self.instance.district:
                self.fields['location'].queryset = Location.objects.filter(district=self.instance.district).order_by('locname')

        if 'state' in self.data:
            try:
                state_id = int(self.data.get('state'))
                self.fields['district'].queryset = District.objects.filter(state_id=state_id).order_by('dist')
            except (ValueError, TypeError):
                pass

        if 'district' in self.data:
            try:
                district_id = int(self.data.get('district'))
                self.fields['location'].queryset = Location.objects.filter(district_id=district_id).order_by('locname')
            except (ValueError, TypeError):
                pass

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip().replace(' ', '').replace('-', '')
        if not INDIAN_PHONE_REGEX.match(phone):
            raise ValidationError("Please enter a valid 10-digit Indian phone number starting with 6, 7, 8, or 9.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        # Verify email is unique except for the current user
        current_user = self.instance.login
        if User.objects.filter(email__iexact=email).exclude(pk=current_user.pk).exists():
            raise ValidationError("This email is already in use by another account.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        # Keep auth.User email and first_name in sync
        user = profile.login
        user.email = profile.email
        user.first_name = profile.contactname
        user.save()
        return profile
