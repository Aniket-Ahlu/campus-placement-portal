from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from core.models import Branch
from .models import StudentProfile
from companies.models import Company

User = get_user_model()


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    
    # Profile fields
    full_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    cgpa = forms.DecimalField(max_digits=4, decimal_places=2, min_value=0.0, max_value=10.0, required=False,
                              widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CGPA (0.00 - 10.00)', 'step': '0.01'}))
    graduation_year = forms.IntegerField(min_value=2020, max_value=2035, required=False,
                                         widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Graduation Year (e.g. 2026)'}))
    resume_link = forms.URLField(required=False, widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://drive.google.com/...'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.ROLE_STUDENT  # Enforce role
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                full_name=self.cleaned_data.get('full_name', ''),
                branch=self.cleaned_data.get('branch'),
                cgpa=self.cleaned_data.get('cgpa'),
                graduation_year=self.cleaned_data.get('graduation_year'),
                resume_link=self.cleaned_data.get('resume_link', ''),
                phone=self.cleaned_data.get('phone', '')
            )
        return user


class RecruiterRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    
    # Company fields
    company_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}))
    company_website = forms.URLField(widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://company.com'}))
    company_industry = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Software, Finance, Healthcare'}))
    company_location = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bengaluru, India'}))
    company_description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description of the organization'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Work Email'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.ROLE_RECRUITER  # Enforce role
        if commit:
            user.save()
            Company.objects.create(
                owner=user,
                name=self.cleaned_data['company_name'],
                website=self.cleaned_data['company_website'],
                industry=self.cleaned_data['company_industry'],
                location=self.cleaned_data['company_location'],
                description=self.cleaned_data['company_description'],
                status=Company.STATUS_PENDING
            )
        return user


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['full_name', 'branch', 'cgpa', 'graduation_year', 'resume_link', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'cgpa': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CGPA (0.00 to 10.00)', 'step': '0.01'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Graduation Year (e.g. 2026)'}),
            'resume_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }
