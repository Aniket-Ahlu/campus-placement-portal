from django import forms
from .models import JobPosting
from core.models import Branch


class JobPostingForm(forms.ModelForm):
    allowed_branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text="Select allowed branches. Leave empty to allow all branches."
    )

    class Meta:
        model = JobPosting
        fields = [
            'title', 'job_type', 'location', 'salary_or_stipend',
            'min_cgpa', 'allowed_branches', 'graduation_year', 'deadline',
            'description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title (e.g. Software Development Engineer)'}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bengaluru / Hybrid / Remote'}),
            'salary_or_stipend': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 14 LPA or ₹40,000 / month'}),
            'min_cgpa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00', 'max': '10.00'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2026 (Optional)'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Detailed job description, responsibilities, and requirements...'}),
        }
