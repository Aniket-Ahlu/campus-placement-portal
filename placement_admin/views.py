from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth import get_user_model
from core.decorators import admin_required
from companies.models import Company
from jobs.models import JobPosting
from applications.models import Application
from .models import AdminActionLog

User = get_user_model()


@admin_required
def admin_dashboard(request):
    """
    Placement Admin Dashboard: pending moderation counts, system overview, and recent actions.
    """
    pending_companies = Company.objects.filter(status=Company.STATUS_PENDING)
    pending_postings = JobPosting.objects.filter(status=JobPosting.STATUS_PENDING)

    total_companies = Company.objects.count()
    approved_companies = Company.objects.filter(status=Company.STATUS_APPROVED).count()
    total_postings = JobPosting.objects.count()
    approved_postings = JobPosting.objects.filter(status=JobPosting.STATUS_APPROVED).count()
    total_applications = Application.objects.count()

    recent_actions = AdminActionLog.objects.order_by('-timestamp')[:6]

    context = {
        'pending_companies_count': pending_companies.count(),
        'pending_postings_count': pending_postings.count(),
        'total_companies': total_companies,
        'approved_companies': approved_companies,
        'total_postings': total_postings,
        'approved_postings': approved_postings,
        'total_applications': total_applications,
        'recent_pending_companies': pending_companies.order_by('-created_at')[:5],
        'recent_pending_postings': pending_postings.select_related('company').order_by('-created_at')[:5],
        'recent_actions': recent_actions,
    }
    return render(request, 'placement_admin/dashboard.html', context)


@admin_required
def pending_companies_queue(request):
    """
    Moderation queue for companies pending approval.
    """
    status_filter = request.GET.get('status', Company.STATUS_PENDING)
    companies = Company.objects.select_related('owner')
    if status_filter:
        companies = companies.filter(status=status_filter)
    companies = companies.order_by('-created_at')

    paginator = Paginator(companies, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'placement_admin/companies_queue.html', {
        'page_obj': page_obj,
        'selected_status': status_filter,
        'pending_count': Company.objects.filter(status=Company.STATUS_PENDING).count(),
    })


@admin_required
def moderate_company(request, pk):
    """
    Approve or reject a company. Rejection requires a non-empty reason.
    Records an immutable AdminActionLog entry.
    """
    if request.method != 'POST':
        return redirect('placement_admin:companies_queue')

    company = get_object_or_404(Company, pk=pk)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()

    if action == 'APPROVE':
        with transaction.atomic():
            company.status = Company.STATUS_APPROVED
            company.rejection_reason = ''
            company.save()

            AdminActionLog.objects.create(
                admin_user=request.user,
                admin_id=request.user.id,
                admin_username=request.user.username,
                action=AdminActionLog.ACTION_APPROVED,
                target_type=AdminActionLog.TARGET_COMPANY,
                target_id=company.id,
                target_label=company.name,
                reason=reason or 'Approved by Placement Admin.'
            )
        messages.success(request, f"Company '{company.name}' has been approved.")
    elif action == 'REJECT':
        if not reason:
            messages.error(request, "A rejection reason is strictly required.")
            return redirect('placement_admin:companies_queue')

        with transaction.atomic():
            company.status = Company.STATUS_REJECTED
            company.rejection_reason = reason
            company.save()

            AdminActionLog.objects.create(
                admin_user=request.user,
                admin_id=request.user.id,
                admin_username=request.user.username,
                action=AdminActionLog.ACTION_REJECTED,
                target_type=AdminActionLog.TARGET_COMPANY,
                target_id=company.id,
                target_label=company.name,
                reason=reason
            )
        messages.warning(request, f"Company '{company.name}' has been rejected.")
    else:
        messages.error(request, "Invalid moderation action.")

    return redirect('placement_admin:companies_queue')


@admin_required
def pending_postings_queue(request):
    """
    Moderation queue for job postings pending approval.
    """
    status_filter = request.GET.get('status', JobPosting.STATUS_PENDING)
    postings = JobPosting.objects.select_related('company', 'company__owner')
    if status_filter:
        postings = postings.filter(status=status_filter)
    postings = postings.order_by('-created_at')

    paginator = Paginator(postings, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'placement_admin/postings_queue.html', {
        'page_obj': page_obj,
        'selected_status': status_filter,
        'pending_count': JobPosting.objects.filter(status=JobPosting.STATUS_PENDING).count(),
    })


@admin_required
def admin_posting_detail(request, pk):
    """
    Detailed inspection view of a job posting for placement admin.
    """
    posting = get_object_or_404(
        JobPosting.objects.select_related('company', 'company__owner').prefetch_related('allowed_branches'),
        pk=pk
    )
    return render(request, 'placement_admin/posting_detail.html', {
        'posting': posting,
    })


@admin_required
def moderate_posting(request, pk):
    """
    Approve or reject a job posting. Rejection requires a non-empty reason.
    Records an immutable AdminActionLog entry.
    """
    if request.method != 'POST':
        return redirect('placement_admin:postings_queue')

    posting = get_object_or_404(JobPosting, pk=pk)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()

    if action == 'APPROVE':
        with transaction.atomic():
            posting.status = JobPosting.STATUS_APPROVED
            posting.rejection_reason = ''
            posting.save()

            AdminActionLog.objects.create(
                admin_user=request.user,
                admin_id=request.user.id,
                admin_username=request.user.username,
                action=AdminActionLog.ACTION_APPROVED,
                target_type=AdminActionLog.TARGET_JOB_POSTING,
                target_id=posting.id,
                target_label=f"{posting.title} ({posting.company.name})",
                reason=reason or 'Approved by Placement Admin.'
            )
        messages.success(request, f"Posting '{posting.title}' has been approved.")
    elif action == 'REJECT':
        if not reason:
            messages.error(request, "A rejection reason is strictly required.")
            return redirect('placement_admin:posting_detail', pk=pk)

        with transaction.atomic():
            posting.status = JobPosting.STATUS_REJECTED
            posting.rejection_reason = reason
            posting.save()

            AdminActionLog.objects.create(
                admin_user=request.user,
                admin_id=request.user.id,
                admin_username=request.user.username,
                action=AdminActionLog.ACTION_REJECTED,
                target_type=AdminActionLog.TARGET_JOB_POSTING,
                target_id=posting.id,
                target_label=f"{posting.title} ({posting.company.name})",
                reason=reason
            )
        messages.warning(request, f"Posting '{posting.title}' has been rejected.")
    else:
        messages.error(request, "Invalid moderation action.")

    return redirect('placement_admin:postings_queue')


@admin_required
def audit_logs(request):
    """
    Audit log page: filterable by action type and target type, paginated, shows admin ID and timestamp.
    """
    logs = AdminActionLog.objects.all().order_by('-timestamp')

    action_filter = request.GET.get('action', '').strip()
    if action_filter in [AdminActionLog.ACTION_APPROVED, AdminActionLog.ACTION_REJECTED]:
        logs = logs.filter(action=action_filter)

    target_filter = request.GET.get('target_type', '').strip()
    if target_filter in [AdminActionLog.TARGET_COMPANY, AdminActionLog.TARGET_JOB_POSTING]:
        logs = logs.filter(target_type=target_filter)

    paginator = Paginator(logs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'placement_admin/audit_logs.html', {
        'page_obj': page_obj,
        'action_choices': AdminActionLog.ACTION_CHOICES,
        'target_choices': AdminActionLog.TARGET_TYPE_CHOICES,
        'selected_action': action_filter,
        'selected_target': target_filter,
        'total_logs': paginator.count,
    })


@admin_required
def users_list(request):
    """
    Read-only list of all registered users by role.
    """
    users = User.objects.all().select_related('student_profile').order_by('-date_joined')

    role_filter = request.GET.get('role', '').strip()
    if role_filter in [User.ROLE_STUDENT, User.ROLE_RECRUITER, User.ROLE_ADMIN]:
        users = users.filter(role=role_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        users = users.filter(username__icontains=search_q) | users.filter(email__icontains=search_q)

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'placement_admin/users_list.html', {
        'page_obj': page_obj,
        'role_choices': User.ROLE_CHOICES,
        'selected_role': role_filter,
        'search_query': search_q,
        'total_users': paginator.count,
    })
