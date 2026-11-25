"""
Forms for Community module (FAQs and Review interactions).
"""

from django import forms
from .models import FAQ


class FAQForm(forms.ModelForm):
    """
    Form for Administrator CRUD operations on Frequently Asked Questions.
    """
    class Meta:
        model = FAQ
        fields = ['faq', 'answer']
        widgets = {
            'faq': forms.TextInput(attrs={
                'class': 'form-control form-control-antique',
                'placeholder': 'e.g. How does Antique Hub verify the authenticity of listed relics?',
                'maxlength': '255',
                'required': True,
                'id': 'id_faq',
            }),
            'answer': forms.Textarea(attrs={
                'class': 'form-control form-control-antique',
                'placeholder': 'Provide a clear, detailed, authoritative answer for collectors and sellers...',
                'rows': 6,
                'required': True,
                'id': 'id_answer',
            }),
        }
        labels = {
            'faq': 'Frequently Asked Question',
            'answer': 'Detailed Answer',
        }
        help_texts = {
            'faq': 'Clear, concise question that antique buyers or sellers frequently ask (min 5 characters).',
            'answer': 'Accurate, thorough response covering platform rules, authenticity standards, or logistics (min 10 characters).',
        }

    def clean_faq(self):
        faq = self.cleaned_data.get('faq', '').strip()
        if len(faq) < 5:
            raise forms.ValidationError("The FAQ question must be at least 5 characters long.")
        return faq

    def clean_answer(self):
        answer = self.cleaned_data.get('answer', '').strip()
        if len(answer) < 10:
            raise forms.ValidationError("The FAQ answer must be at least 10 characters long.")
        return answer
