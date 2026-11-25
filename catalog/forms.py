"""
Forms for Antique Catalog Management (Modules 3 & 4).
Includes:
- CategoryForm & SubCategoryForm (Module 3)
- ItemUploadForm & ItemEditForm (Module 4: Seller Upload with Dual Images, Origin, Age & Stock Creation)
"""

import os
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Category, SubCategory, Item
from inventory.models import Stock

MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']


def validate_image_file(image_file):
    """
    Validates uploaded antique photographs:
    - Maximum file size: 5MB
    - Allowed extensions: JPG, JPEG, PNG, WEBP, GIF
    """
    if not image_file or not hasattr(image_file, 'size'):
        return

    # Check file size
    if image_file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"Image size exceeds {MAX_IMAGE_SIZE_MB}MB limit ({image_file.size / (1024*1024):.1f}MB uploaded). "
            "Please upload a compressed image."
        )

    # Check file extension
    ext = os.path.splitext(image_file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image extension '{ext}'. Only JPG, PNG, and WEBP formats are allowed."
        )


class CategoryForm(forms.ModelForm):
    """
    Form for adding and editing Antique Categories.
    Enforces case-insensitive duplicate name prevention.
    """
    class Meta:
        model = Category
        fields = ['category', 'description']
        widgets = {
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Furniture, Decor, Coins, Jewellery, Artefacts, Collectibles',
                'autofocus': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter category description and historical eras included...',
            }),
        }

    def clean_category(self):
        cat_name = self.cleaned_data.get('category', '').strip()
        if len(cat_name) < 2:
            raise ValidationError("Category name must be at least 2 characters long.")

        qs = Category.objects.filter(category__iexact=cat_name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError(f"An antique category named '{cat_name}' already exists.")
        return cat_name


class SubCategoryForm(forms.ModelForm):
    """
    Form for adding and editing Antique SubCategories.
    Requires selecting a parent Category.
    Enforces case-insensitive duplicate prevention within the chosen Category.
    """
    class Meta:
        model = SubCategory
        fields = ['category', 'subcategory']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Colonial Armchairs, Mughal Mohurs, Persian Rugs',
            }),
        }

    def clean_subcategory(self):
        subcat_name = self.cleaned_data.get('subcategory', '').strip()
        if len(subcat_name) < 2:
            raise ValidationError("Subcategory name must be at least 2 characters long.")
        return subcat_name

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        subcat_name = cleaned_data.get('subcategory')

        if category and subcat_name:
            qs = SubCategory.objects.filter(category=category, subcategory__iexact=subcat_name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    'subcategory',
                    f"A subcategory named '{subcat_name}' already exists under '{category.category}'."
                )
        return cleaned_data


class ItemUploadForm(forms.ModelForm):
    """
    Form for activated Sellers to upload antique listings (Module 4).
    Dual creation: Creating an item also creates its Stock row (DFD 2.1 & 2.2).
    """
    opening_stock = forms.IntegerField(
        min_value=0,
        initial=1,
        label="Opening Stock Quantity",
        help_text="Units available for sale. If 0, status automatically switches to 'Out of Stock'.",
        error_messages={
            'min_value': 'Opening stock quantity cannot be negative.'
        },
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
    )

    class Meta:
        model = Item
        fields = [
            'item',
            'title',
            'category',
            'subcategory',
            'years_old',
            'origin',
            'price',
            'status',
            'img1',
            'img2',
            'description',
        ]
        widgets = {
            'item': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. ANT-1890-CHAIR or SKU Code',
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 1890 Victorian Hand-Carved Teak Armchair',
            }),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'subcategory': forms.Select(attrs={'class': 'form-select', 'id': 'id_subcategory'}),
            'years_old': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 135',
                'min': '1',
            }),
            'origin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. British India, Madras Presidency or Mughal Dynasty',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 45000.00',
                'step': '0.01',
                'min': '1',
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'img1': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'img2': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Detail historical era, material provenance, craftsmanship, and physical condition...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamic subcategory population if category submitted via POST
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = SubCategory.objects.filter(category_id=category_id).order_by('subcategory')
            except (ValueError, TypeError):
                self.fields['subcategory'].queryset = SubCategory.objects.none()
        else:
            self.fields['subcategory'].queryset = SubCategory.objects.none()

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price

    def clean_opening_stock(self):
        stock = self.cleaned_data.get('opening_stock')
        if stock is not None and stock < 0:
            raise ValidationError("Opening stock quantity cannot be negative.")
        return stock

    def clean_years_old(self):
        years = self.cleaned_data.get('years_old')
        if years is not None and years < 1:
            raise ValidationError("Age of antique item must be at least 1 year old.")
        return years

    def clean_img1(self):
        img1 = self.cleaned_data.get('img1')
        validate_image_file(img1)
        return img1

    def clean_img2(self):
        img2 = self.cleaned_data.get('img2')
        if img2:
            validate_image_file(img2)
        return img2

    @transaction.atomic
    def save(self, seller_user, commit=True):
        """
        Dual Creation (DFD 2.1 & 2.2):
        Saves Item and immediately initializes matching Stock ledger record.
        """
        item = super().save(commit=False)
        item.seller = seller_user

        opening_stock = self.cleaned_data.get('opening_stock', 1)

        # If opening stock is zero, auto-switch status to 'Out of Stock'
        if opening_stock == 0 and item.status == 'Available':
            item.status = 'Out of Stock'

        if commit:
            item.save()

            # DFD 2.2: Create Stock row
            Stock.objects.create(
                item=item,
                tot_arr_stock=opening_stock,
                cur_stock=opening_stock,
                status='In Stock' if opening_stock > 0 else 'Out of Stock'
            )

        return item


class ItemEditForm(forms.ModelForm):
    """
    Form for editing an existing antique item and adjusting its current stock.
    """
    current_stock = forms.IntegerField(
        min_value=0,
        label="Current Available Stock",
        error_messages={
            'min_value': 'Current stock cannot be negative.'
        },
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Item
        fields = [
            'item',
            'title',
            'category',
            'subcategory',
            'years_old',
            'origin',
            'price',
            'status',
            'img1',
            'img2',
            'description',
        ]
        widgets = {
            'item': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'subcategory': forms.Select(attrs={'class': 'form-select', 'id': 'id_subcategory'}),
            'years_old': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '1'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'img1': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'img2': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-fill subcategories for current category
        if self.instance and self.instance.category:
            self.fields['subcategory'].queryset = SubCategory.objects.filter(
                category=self.instance.category
            ).order_by('subcategory')

        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = SubCategory.objects.filter(
                    category_id=category_id
                ).order_by('subcategory')
            except (ValueError, TypeError):
                pass

        # Pre-fill current_stock from Stock ledger
        if self.instance and self.instance.pk:
            latest_stock = self.instance.stock_records.first()
            if latest_stock:
                self.fields['current_stock'].initial = latest_stock.cur_stock
            else:
                self.fields['current_stock'].initial = 0

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price

    def clean_current_stock(self):
        stock = self.cleaned_data.get('current_stock')
        if stock is not None and stock < 0:
            raise ValidationError("Current stock cannot be negative.")
        return stock

    def clean_img1(self):
        img1 = self.cleaned_data.get('img1')
        if img1 and hasattr(img1, 'size'):
            validate_image_file(img1)
        return img1

    def clean_img2(self):
        img2 = self.cleaned_data.get('img2')
        if img2 and hasattr(img2, 'size'):
            validate_image_file(img2)
        return img2

    @transaction.atomic
    def save(self, commit=True):
        item = super().save(commit=False)
        new_stock = self.cleaned_data.get('current_stock')

        if new_stock == 0 and item.status == 'Available':
            item.status = 'Out of Stock'
        elif new_stock > 0 and item.status == 'Out of Stock':
            item.status = 'Available'

        if commit:
            item.save()

            # Update or create Stock ledger entry
            stock_record = item.stock_records.first()
            if stock_record:
                if new_stock > stock_record.tot_arr_stock:
                    stock_record.tot_arr_stock = new_stock
                stock_record.cur_stock = new_stock
                stock_record.save()
            else:
                Stock.objects.create(
                    item=item,
                    tot_arr_stock=new_stock,
                    cur_stock=new_stock,
                    status='In Stock' if new_stock > 0 else 'Out of Stock'
                )

        return item
