from django import forms
from django.core.exceptions import ValidationError


class AddStockForm(forms.Form):
    """
    Form for adding stock units (Restocking) to an existing antique artifact.
    Used by both Sellers (for their own items) and Admins (for any item).
    """
    quantity_to_add = forms.IntegerField(
        min_value=1,
        label="Units to Add *",
        error_messages={
            'min_value': 'Quantity to add must be at least 1 unit.',
            'required': 'Please enter the number of units to add.',
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter quantity (e.g. 2)',
            'min': '1',
            'autofocus': True,
        }),
        help_text="This quantity will increase both Total Arrived Stock and Current Available Stock."
    )
    notes = forms.CharField(
        required=False,
        max_length=255,
        label="Restock Reference / Note (Optional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Consignment Batch #2026-B or Auction acquisition',
        })
    )

    def clean_quantity_to_add(self):
        quantity = self.cleaned_data.get('quantity_to_add')
        if quantity is not None and quantity <= 0:
            raise ValidationError("Quantity to add must be greater than zero.")
        return quantity


class DiscountForm(forms.ModelForm):
    """
    Module 12: Admin "Add Discount of Items" form.
    Allows choosing an applicable category (or all for storewide discount),
    discount percent (1% to 90%), start date, and end date with date ordering validation.
    """
    class Meta:
        from .models import Discount
        model = Discount
        fields = ['applicable_cat', 'discount_percent', 'startdate', 'enddate']
        widgets = {
            'applicable_cat': forms.Select(attrs={
                'class': 'form-select form-select-antique',
                'id': 'id_applicable_cat',
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'form-control form-control-antique',
                'placeholder': 'Enter discount percentage (1 to 90)',
                'min': '1',
                'max': '90',
                'step': '0.5',
                'required': True,
                'id': 'id_discount_percent',
            }),
            'startdate': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control form-control-antique',
                'required': True,
                'id': 'id_startdate',
            }),
            'enddate': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control form-control-antique',
                'required': True,
                'id': 'id_enddate',
            }),
        }
        labels = {
            'applicable_cat': 'Applicable Antique Category',
            'discount_percent': 'Promotional Discount Percentage (%)',
            'startdate': 'Campaign Start Date',
            'enddate': 'Campaign End Date',
        }
        help_texts = {
            'applicable_cat': 'Select a specific antique category, or leave blank to apply this discount across All Categories.',
            'discount_percent': 'Enter a promotional discount percentage strictly between 1% and 90%.',
            'startdate': 'Date from which the discount goes live.',
            'enddate': 'Date until which the discount remains active. Must be strictly after start date.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applicable_cat'].empty_label = "-- All Antique Categories (Storewide Discount) --"
        self.fields['applicable_cat'].required = False

    def clean_discount_percent(self):
        percent = self.cleaned_data.get('discount_percent')
        if percent is not None:
            if percent < 1 or percent > 90:
                raise ValidationError("Discount percent must be between 1% and 90%.")
        return percent

    def clean(self):
        cleaned_data = super().clean()
        startdate = cleaned_data.get('startdate')
        enddate = cleaned_data.get('enddate')

        if startdate and enddate:
            if enddate <= startdate:
                self.add_error('enddate', "End date must be strictly after the campaign start date.")

        return cleaned_data

