"""
Forms for Admin Locations Management.
Implements validation for:
- State (DFD 1.1.1)
- District (needs a state, DFD 1.1.2)
- Location (needs a district, DFD 1.1.3)
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import State, District, Location


class StateForm(forms.ModelForm):
    """
    Form to create and edit States.
    """
    class Meta:
        model = State
        fields = ['state']
        widgets = {
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter state name (e.g. Karnataka)',
                'autofocus': True,
            }),
        }

    def clean_state(self):
        state_name = self.cleaned_data.get('state', '').strip()
        if len(state_name) < 2:
            raise ValidationError("State name must be at least 2 characters long.")

        # Check duplicate case-insensitively, excluding current instance if editing
        qs = State.objects.filter(state__iexact=state_name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError(f"A state with the name '{state_name}' already exists.")
        return state_name


class DistrictForm(forms.ModelForm):
    """
    Form to create and edit Districts. Requires selecting a parent State.
    """
    class Meta:
        model = District
        fields = ['state', 'dist']
        widgets = {
            'state': forms.Select(attrs={'class': 'form-select'}),
            'dist': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter district name (e.g. Mysuru)',
            }),
        }

    def clean_dist(self):
        dist_name = self.cleaned_data.get('dist', '').strip()
        if len(dist_name) < 2:
            raise ValidationError("District name must be at least 2 characters long.")
        return dist_name

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        dist_name = cleaned_data.get('dist')

        if state and dist_name:
            qs = District.objects.filter(state=state, dist__iexact=dist_name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error('dist', f"District '{dist_name}' already exists in state '{state.state}'.")
        return cleaned_data


class LocationForm(forms.ModelForm):
    """
    Form to create and edit Locations. Requires selecting District (with State selector helper).
    """
    state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        empty_label="-- Filter by State --",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_state_filter'}),
        help_text="Select a state to filter the districts dropdown"
    )

    class Meta:
        model = Location
        fields = ['district', 'locname']
        widgets = {
            'district': forms.Select(attrs={'class': 'form-select', 'id': 'id_district'}),
            'locname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location / ward / locality (e.g. Palace Road)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-select state if editing existing location
        if self.instance and self.instance.pk and self.instance.district:
            self.fields['state'].initial = self.instance.district.state
            self.fields['district'].queryset = District.objects.filter(state=self.instance.district.state).order_by('dist')

        # Dynamically populate district if state submitted via POST
        if 'state' in self.data:
            try:
                state_id = int(self.data.get('state'))
                self.fields['district'].queryset = District.objects.filter(state_id=state_id).order_by('dist')
            except (ValueError, TypeError):
                pass

    def clean_locname(self):
        loc_name = self.cleaned_data.get('locname', '').strip()
        if len(loc_name) < 2:
            raise ValidationError("Location name must be at least 2 characters long.")
        return loc_name

    def clean(self):
        cleaned_data = super().clean()
        district = cleaned_data.get('district')
        loc_name = cleaned_data.get('locname')

        if district and loc_name:
            qs = Location.objects.filter(district=district, locname__iexact=loc_name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error('locname', f"Location '{loc_name}' already exists in district '{district.dist}'.")
        return cleaned_data
