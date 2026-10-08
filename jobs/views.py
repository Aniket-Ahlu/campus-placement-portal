from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from core.decorators import recruiter_required
from core.models import Branch
from core.eligibility import check_eligibility
from companies.models import Company
from .models import JobPosting
from .forms import JobPostingForm
from applications.models import Application


def browse_postings(request):
    """
    Public and student portal job browsing page.
    Enforces visibility rule: students only see approved postings of approved companies that are open and not expired.
    Provides search, filter by job type, branch, min CGPA, and pagination of 9 per page.
    """
    today = timezone.now().date()
    qs = JobPosting.objects.filter(
        status='APPROVED',
        company__status='APPROVED',
        is_open=True,
        deadline__gte=today
    ).select_related('company').prefetch_related('allowed_branches')

    # Keyword search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(company__name__icontains=q) |
            Q(location__icontains=q)
        )

    # Filter by job type
    job_type = request.GET.get('job_type', '').strip()
    if job_type in [JobPosting.JOB_TYPE_FULLTIME, JobPosting.JOB_TYPE_INTERNSHIP]:
        qs = qs.filter(job_type=job_type)

    # Filter by branch
    branch_id = request.GET.get('branch', '').strip()
    if branch_id.isdigit():
        branch = Branch.objects.filter(id=branch_id).first()
        if branch:
            # Posting is open if allowed_branches is empty OR contains this branch
            qs = qs.filter(Q(allowed_branches__isnull=True) | Q(allowed_branches=branch)).distinct()

    # Filter by max allowed min_cgpa
    min_cgpa = request.GET.get('min_cgpa', '').strip()
    if min_cgpa:
        try:
            cgpa_val = float(min_cgpa)
            qs = qs.filter(min_cgpa__lte=cgpa_val)
        except ValueError:
            pass

    # Sort
    sort = request.GET.get('sort', 'newest')
    if sort == 'deadline':
        qs = qs.order_by('deadline', '-created_at')
    elif sort == 'cgpa_asc':
        qs = qs.order_by('min_cgpa', '-created_at')
    else:
        qs = qs.order_by('-created_at')

    # Pagination: 9 per page
    paginator = Paginator(qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Student eligibility evaluation for card badges
    student_profile = None
    applied_posting_ids = set()
    if request.user.is_authenticated and request.user.is_student:
        student_profile = getattr(request.user, 'student_profile', None)
        applied_posting_ids = set(
            Application.objects.filter(student=request.user).values_list('posting_id', flat=True)
        )

    for posting in page_obj:
        if student_profile:
            reasons = check_eligibility(student_profile, posting)
            posting.is_eligible = (len(reasons) == 0)
            posting.already_applied = (posting.id in applied_posting_ids)
        else:
            posting.is_eligible = None
            posting.already_applied = False

    branches = Branch.objects.all()

    context = {
        'page_obj': page_obj,
        'branches': branches,
        'search_query': q,
        'selected_job_type': job_type,
        'selected_branch': branch_id,
        'selected_min_cgpa': min_cgpa,
        'selected_sort': sort,
        'total_count': paginator.count,
    }
    return render(request, 'jobs/browse.html', context)


def posting_detail(request, pk):
    """
    Job Posting Detail view.
    Rule 1: Students see ONLY postings where posting.status=APPROVED, company.status=APPROVED, is_open, deadline not passed.
    Direct URLs to anything else return 404 for students.
    """
    posting = get_object_or_404(
        JobPosting.objects.select_related('company', 'company__owner').prefetch_related('allowed_branches'),
        pk=pk
    )

    is_student_user = request.user.is_authenticated and request.user.is_student
    is_recruiter_owner = (
        request.user.is_authenticated and
        request.user.is_recruiter and
        posting.company.owner == request.user
    )
    is_admin = request.user.is_authenticated and request.user.is_placement_admin

    # If student or unauthenticated visitor, enforce strict active-approved visibility
    if not (is_recruiter_owner or is_admin):
        today = timezone.now().date()
        if not (
            posting.status == 'APPROVED'
            and posting.company.status == 'APPROVED'
            and posting.is_open
            and posting.deadline >= today
        ):
            raise Http404("Job posting not found or no longer accepting applications.")

    # Student eligibility checking
    eligibility_reasons = []
    has_applied = False
    existing_application = None

    if is_student_user:
        profile = getattr(request.user, 'student_profile', None)
        eligibility_reasons = check_eligibility(profile, posting)
        existing_application = Application.objects.filter(student=request.user, posting=posting).first()
        if existing_application:
            has_applied = True

    context = {
        'posting': posting,
        'is_recruiter_owner': is_recruiter_owner,
        'eligibility_reasons': eligibility_reasons,
        'is_eligible': len(eligibility_reasons) == 0 if is_student_user else False,
        'has_applied': has_applied,
        'existing_application': existing_application,
    }
    return render(request, 'jobs/posting_detail.html', context)


@recruiter_required
def recruiter_dashboard(request):
    """
    Recruiter Dashboard: Summary statistics, company approval status, recent postings & applicants.
    """
    company = Company.objects.filter(owner=request.user).first()
    if not company:
        messages.warning(request, "Please register your company details first.")
        return redirect('companies:profile')

    postings = JobPosting.objects.filter(company=company)
    total_postings = postings.count()
    pending_postings = postings.filter(status='PENDING').count()
    approved_postings = postings.filter(status='APPROVED').count()

    applications = Application.objects.filter(posting__company=company)
    total_applicants = applications.count()
    shortlisted_applicants = applications.filter(status=Application.STATUS_SHORTLISTED).count()
    offered_applicants = applications.filter(status=Application.STATUS_OFFERED).count()

    recent_postings = postings.annotate(app_count=Count('applications')).order_by('-created_at')[:5]
    recent_applications = applications.select_related('student', 'posting', 'student__student_profile').order_by('-applied_at')[:5]

    context = {
        'company': company,
        'total_postings': total_postings,
        'pending_postings': pending_postings,
        'approved_postings': approved_postings,
        'total_applicants': total_applicants,
        'shortlisted_applicants': shortlisted_applicants,
        'offered_applicants': offered_applicants,
        'recent_postings': recent_postings,
        'recent_applications': recent_applications,
    }
    return render(request, 'jobs/recruiter_dashboard.html', context)


@recruiter_required
def recruiter_postings_list(request):
    """
    List of all postings created by the recruiter's company.
    """
    company = Company.objects.filter(owner=request.user).first()
    if not company:
        messages.warning(request, "Please set up your company profile first.")
        return redirect('companies:profile')

    postings = JobPosting.objects.filter(company=company).annotate(
        applicant_count=Count('applications')
    ).order_by('-created_at')

    return render(request, 'jobs/recruiter_postings.html', {
        'company': company,
        'postings': postings,
    })


@recruiter_required
def recruiter_posting_create(request):
    """
    Create a new job posting.
    Rule 2: Recruiters can create postings ONLY after their company is APPROVED.
    """
    company = Company.objects.filter(owner=request.user).first()
    if not company or company.status != Company.STATUS_APPROVED:
        messages.error(
            request,
            "Your company profile must be approved by the Placement Admin before you can post jobs or internships."
        )
        return redirect('jobs:recruiter_dashboard')

    if request.method == 'POST':
        form = JobPostingForm(request.POST)
        if form.is_valid():
            posting = form.save(commit=False)
            posting.company = company
            posting.status = JobPosting.STATUS_PENDING
            posting.is_open = True
            posting.save()
            form.save_m2m()
            messages.success(request, f"Posting '{posting.title}' created and submitted for admin approval.")
            return redirect('jobs:recruiter_postings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = JobPostingForm()

    return render(request, 'jobs/posting_form.html', {
        'form': form,
        'title': 'Create New Job/Internship Posting',
        'is_edit': False,
    })


@recruiter_required
def recruiter_posting_edit(request, pk):
    """
    Edit an existing posting.
    Object-level security: must belong to the recruiter's company.
    Rule 2: Editing an approved posting resets it to PENDING. A rejected posting can be edited and resubmitted.
    """
    company = Company.objects.filter(owner=request.user).first()
    posting = get_object_or_404(JobPosting, pk=pk, company=company)

    was_approved = (posting.status == JobPosting.STATUS_APPROVED)
    was_rejected = (posting.status == JobPosting.STATUS_REJECTED)

    if request.method == 'POST':
        form = JobPostingForm(request.POST, instance=posting)
        if form.is_valid():
            inst = form.save(commit=False)
            if was_approved:
                inst.status = JobPosting.STATUS_PENDING
                inst.rejection_reason = ''
                messages.warning(request, "Core posting details modified. Posting has been reset to PENDING for admin review.")
            elif was_rejected:
                inst.status = JobPosting.STATUS_PENDING
                inst.rejection_reason = ''
                messages.info(request, "Rejected posting updated and resubmitted for admin review.")
            else:
                messages.success(request, "Posting details updated.")

            inst.save()
            form.save_m2m()
            return redirect('jobs:recruiter_postings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = JobPostingForm(instance=posting)

    return render(request, 'jobs/posting_form.html', {
        'form': form,
        'posting': posting,
        'title': f"Edit Posting: {posting.title}",
        'is_edit': True,
    })


@recruiter_required
def recruiter_posting_toggle(request, pk):
    """
    Close or reopen a job posting.
    """
    if request.method != 'POST':
        return redirect('jobs:recruiter_postings')

    company = Company.objects.filter(owner=request.user).first()
    posting = get_object_or_404(JobPosting, pk=pk, company=company)

    posting.is_open = not posting.is_open
    posting.save()
    status_str = "reopened" if posting.is_open else "closed"
    messages.success(request, f"Posting '{posting.title}' has been {status_str}.")
    return redirect('jobs:recruiter_postings')
