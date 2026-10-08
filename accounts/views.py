from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.decorators import student_required
from .forms import StudentRegistrationForm, RecruiterRegistrationForm, StudentProfileForm
from .models import StudentProfile
from applications.models import Application
from jobs.models import JobPosting
from django.utils import timezone


def user_login(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_redirect')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('core:dashboard_redirect')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('core:landing')


def register_student(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_redirect')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully! Please verify your profile details.")
            return redirect('accounts:student_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register_student.html', {'form': form})


def register_recruiter(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_redirect')

    if request.method == 'POST':
        form = RecruiterRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Recruiter account created! Your company registration is pending admin approval.")
            return redirect('jobs:recruiter_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RecruiterRegistrationForm()

    return render(request, 'accounts/register_recruiter.html', {'form': form})


@student_required
def student_dashboard(request):
    student = request.user
    profile, _ = StudentProfile.objects.get_or_create(user=student)
    
    applications = Application.objects.filter(student=student).select_related('posting', 'posting__company')
    total_apps = applications.count()
    shortlisted_count = applications.filter(status=Application.STATUS_SHORTLISTED).count()
    offers_count = applications.filter(status=Application.STATUS_OFFERED).count()
    interviews_count = applications.filter(status=Application.STATUS_INTERVIEW).count()

    recent_applications = applications.order_by('-applied_at')[:5]

    # Available jobs that student might be interested in
    open_postings = JobPosting.objects.filter(
        status='APPROVED',
        company__status='APPROVED',
        is_open=True,
        deadline__gte=timezone.now().date()
    ).exclude(applications__student=student).order_by('-created_at')[:4]

    context = {
        'profile': profile,
        'total_apps': total_apps,
        'shortlisted_count': shortlisted_count,
        'offers_count': offers_count,
        'interviews_count': interviews_count,
        'recent_applications': recent_applications,
        'open_postings': open_postings,
    }
    return render(request, 'accounts/student_dashboard.html', context)


@student_required
def student_profile(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:student_profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
    })
