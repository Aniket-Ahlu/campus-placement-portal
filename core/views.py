from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from jobs.models import JobPosting
from companies.models import Company


def landing(request):
    """
    Public landing page: Hero section, role cards, portal stats, how it works.
    """
    approved_postings_count = JobPosting.objects.filter(status='APPROVED', is_open=True).count()
    approved_companies_count = Company.objects.filter(status='APPROVED').count()

    context = {
        'total_postings': approved_postings_count,
        'total_companies': approved_companies_count,
    }
    return render(request, 'core/landing.html', context)


@login_required
def dashboard_redirect(request):
    """
    Redirects authenticated users to their corresponding dashboard based on their role.
    """
    user = request.user
    if user.is_placement_admin:
        return redirect('placement_admin:dashboard')
    elif user.is_recruiter:
        return redirect('jobs:recruiter_dashboard')
    elif user.is_student:
        return redirect('accounts:student_dashboard')
    return redirect('core:landing')


def error_403_view(request, exception=None):
    return render(request, '403.html', {'message': 'You do not have permission to access this resource.'}, status=403)


def error_404_view(request, exception=None):
    return render(request, '404.html', {'message': 'The page or resource you requested could not be found.'}, status=404)


def error_500_view(request):
    return render(request, '500.html', {'message': 'A server error occurred. Please contact the administrator.'}, status=500)
