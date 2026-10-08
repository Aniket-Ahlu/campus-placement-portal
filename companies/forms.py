from django import forms
from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'website', 'industry', 'location', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://company.com'}),
            'industry': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Information Technology'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bengaluru, India'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Company overview, vision, and domain'}),
        }
