from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from core.decorators import student_required, recruiter_required
from core.eligibility import check_eligibility
from jobs.models import JobPosting
from .models import Application, ApplicationStatusHistory


@student_required
def apply_confirm(request, posting_id):
    """
    Student application view.
    Checks eligibility server-side; if ineligible, blocks application and presents errors.
    On valid submission, creates Application and ApplicationStatusHistory.
    """
    posting = get_object_or_404(JobPosting, pk=posting_id)
    profile = getattr(request.user, 'student_profile', None)

    # First check if unapproved or expired
    today = timezone.now().date()
    if not (
        posting.status == 'APPROVED'
        and posting.company.status == 'APPROVED'
        and posting.is_open
        and posting.deadline >= today
    ):
        raise Http404("Posting is not accepting applications.")

    reasons = check_eligibility(profile, posting)

    if request.method == 'POST':
        if reasons:
            messages.error(request, f"Submission blocked: {reasons[0]}")
            return render(request, 'applications/apply_confirm.html', {
                'posting': posting,
                'profile': profile,
                'reasons': reasons,
                'is_eligible': False,
            }, status=400)

        # Check duplicate
        if Application.objects.filter(student=request.user, posting=posting).exists():
            messages.warning(request, "You have already applied to this posting.")
            return redirect('applications:my_applications')

        with transaction.atomic():
            app = Application.objects.create(
                student=request.user,
                posting=posting,
                status=Application.STATUS_APPLIED
            )
            ApplicationStatusHistory.objects.create(
                application=app,
                old_status='NONE',
                new_status=Application.STATUS_APPLIED,
                changed_by=request.user,
                note='Application submitted by student.'
            )

        messages.success(request, f"Successfully applied for {posting.title} at {posting.company.name}!")
        return redirect('applications:detail', pk=app.pk)

    return render(request, 'applications/apply_confirm.html', {
        'posting': posting,
        'profile': profile,
        'reasons': reasons,
        'is_eligible': len(reasons) == 0,
    })


@student_required
def my_applications(request):
    """
    List of student's own applications with status badges and filters.
    """
    status_filter = request.GET.get('status', '').strip()
    apps = Application.objects.filter(student=request.user).select_related('posting', 'posting__company')

    if status_filter:
        apps = apps.filter(status=status_filter)

    status_choices = Application.STATUS_CHOICES

    return render(request, 'applications/my_applications.html', {
        'applications': apps,
        'status_choices': status_choices,
        'selected_status': status_filter,
    })


@student_required
def application_detail(request, pk):
    """
    Detail page for student application, displaying visual timeline and withdraw option.
    Object-level security: only owner can view.
    """
    app = get_object_or_404(
        Application.objects.select_related('posting', 'posting__company'),
        pk=pk,
        student=request.user
    )

    history = app.status_history.order_by('changed_at')

    # Visual pipeline steps definition
    pipeline_steps = [
        ('APPLIED', 'Applied'),
        ('UNDER_REVIEW', 'Under Review'),
        ('SHORTLISTED', 'Shortlisted'),
        ('INTERVIEW', 'Interview'),
        ('OFFERED', 'Offered'),
    ]

    return render(request, 'applications/application_detail.html', {
        'application': app,
        'history': history,
        'pipeline_steps': pipeline_steps,
    })


@student_required
def withdraw_application(request, pk):
    """
    Allows student to withdraw an active, non-final application.
    """
    if request.method != 'POST':
        return redirect('applications:detail', pk=pk)

    app = get_object_or_404(Application, pk=pk, student=request.user)

    if app.is_final:
        messages.error(request, f"Cannot withdraw: application is already in final state ({app.get_status_display()}).")
        return redirect('applications:detail', pk=pk)

    old_status = app.status
    app.status = Application.STATUS_WITHDRAWN
    app.save()

    ApplicationStatusHistory.objects.create(
        application=app,
        old_status=old_status,
        new_status=Application.STATUS_WITHDRAWN,
        changed_by=request.user,
        note='Application withdrawn by candidate.'
    )

    messages.info(request, "Application withdrawn successfully.")
    return redirect('applications:detail', pk=pk)


@student_required
def status_feed(request):
    """
    Real-time JSON endpoint polled every 15s by student's browser.
    Returns only the logged-in student's own applications and status updates.
    """
    apps = Application.objects.filter(student=request.user).select_related('posting', 'posting__company')
    data = []
    for app in apps:
        latest_history = app.status_history.order_by('-changed_at').first()
        data.append({
            'id': app.id,
            'posting_id': app.posting.id,
            'posting_title': app.posting.title,
            'company_name': app.posting.company.name,
            'status': app.status,
            'status_display': app.get_status_display(),
            'badge_class': app.badge_class,
            'is_final': app.is_final,
            'can_withdraw': app.can_withdraw,
            'updated_at': app.updated_at.strftime('%b %d, %Y, %I:%M %p'),
            'last_note': latest_history.note if latest_history else '',
        })

    return JsonResponse({
        'timestamp': timezone.now().isoformat(),
        'count': len(data),
        'applications': data,
    })


@recruiter_required
def recruiter_posting_applicants(request, posting_id):
    """
    Recruiter's view of applicants for a specific posting.
    Object-level security: posting must belong to recruiter's company.
    Supports filtering by status, sorting by CGPA, and batch status updating.
    """
    posting = get_object_or_404(
        JobPosting.objects.select_related('company'),
        pk=posting_id,
        company__owner=request.user
    )

    apps = Application.objects.filter(posting=posting).select_related(
        'student', 'student__student_profile', 'student__student_profile__branch'
    )

    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        apps = apps.filter(status=status_filter)

    # Sort
    sort = request.GET.get('sort', 'applied_desc')
    if sort == 'cgpa_desc':
        apps = apps.order_by('-student__student_profile__cgpa', '-applied_at')
    elif sort == 'cgpa_asc':
        apps = apps.order_by('student__student_profile__cgpa', '-applied_at')
    elif sort == 'name_asc':
        apps = apps.order_by('student__student_profile__full_name', '-applied_at')
    else:
        apps = apps.order_by('-applied_at')

    # Batch Update handling
    if request.method == 'POST' and 'batch_update' in request.POST:
        selected_ids = request.POST.getlist('selected_applicants')
        target_status = request.POST.get('target_status', '').strip()
        batch_note = request.POST.get('batch_note', '').strip()

        if not selected_ids:
            messages.warning(request, "No applicants were selected for batch update.")
            return redirect(request.get_full_path())

        if not target_status:
            messages.warning(request, "Please select a target status for batch update.")
            return redirect(request.get_full_path())

        updated_count = 0
        skipped_count = 0
        skip_reasons = []

        target_apps = Application.objects.filter(id__in=selected_ids, posting=posting)
        for app in target_apps:
            allowed, err_msg = app.can_transition_to(target_status, request.user)
            if allowed:
                old_st = app.status
                app.status = target_status
                if batch_note:
                    app.recruiter_note = batch_note
                app.save()

                ApplicationStatusHistory.objects.create(
                    application=app,
                    old_status=old_st,
                    new_status=target_status,
                    changed_by=request.user,
                    note=batch_note or f"Batch updated to {dict(Application.STATUS_CHOICES).get(target_status)}"
                )
                updated_count += 1
            else:
                skipped_count += 1
                skip_reasons.append(f"#{app.id} ({app.get_status_display()}): {err_msg}")

        if updated_count and skipped_count:
            messages.warning(request, f"{updated_count} updated, {skipped_count} skipped: invalid transition.")
        elif updated_count:
            messages.success(request, f"Successfully updated {updated_count} applicants to {dict(Application.STATUS_CHOICES).get(target_status)}.")
        else:
            messages.error(request, f"0 updated, {skipped_count} skipped: invalid transition.")

        return redirect(request.get_full_path())

    status_choices = Application.STATUS_CHOICES
    transition_targets = [
        (Application.STATUS_UNDER_REVIEW, 'Under Review'),
        (Application.STATUS_SHORTLISTED, 'Shortlisted'),
        (Application.STATUS_INTERVIEW, 'Interview Scheduled'),
        (Application.STATUS_OFFERED, 'Offer Extended'),
        (Application.STATUS_REJECTED, 'Rejected'),
    ]

    return render(request, 'applications/recruiter_applicants.html', {
        'posting': posting,
        'applications': apps,
        'status_choices': status_choices,
        'transition_targets': transition_targets,
        'selected_status': status_filter,
        'selected_sort': sort,
        'total_count': apps.count(),
    })


@recruiter_required
def recruiter_applicant_detail(request, pk):
    """
    Recruiter's view of a single applicant, allowing single status transition and recruiter note update.
    Object-level security: posting must belong to recruiter's company.
    """
    app = get_object_or_404(
        Application.objects.select_related(
            'student', 'posting', 'posting__company',
            'student__student_profile', 'student__student_profile__branch'
        ),
        pk=pk,
        posting__company__owner=request.user
    )

    profile = getattr(app.student, 'student_profile', None)
    history = app.status_history.order_by('changed_at')

    # Allowed transitions for this applicant's current state
    allowed_transitions = Application.ALLOWED_RECRUITER_TRANSITIONS.get(app.status, [])
    allowed_choices = [(st, dict(Application.STATUS_CHOICES).get(st, st)) for st in allowed_transitions]

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        recruiter_note = request.POST.get('recruiter_note', '').strip()

        # Update note even if status doesn't change
        app.recruiter_note = recruiter_note

        if new_status and new_status != app.status:
            allowed, err_msg = app.can_transition_to(new_status, request.user)
            if not allowed:
                messages.error(request, f"Invalid transition: {err_msg}")
            else:
                old_status = app.status
                app.status = new_status
                app.save()

                ApplicationStatusHistory.objects.create(
                    application=app,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    note=recruiter_note or f"Status changed to {dict(Application.STATUS_CHOICES).get(new_status)}"
                )
                messages.success(request, f"Status updated to {app.get_status_display()}.")
                return redirect('applications:recruiter_applicant_detail', pk=app.pk)
        else:
            app.save()
            messages.success(request, "Recruiter note saved.")
            return redirect('applications:recruiter_applicant_detail', pk=app.pk)

    return render(request, 'applications/recruiter_applicant_detail.html', {
        'application': app,
        'profile': profile,
        'history': history,
        'allowed_choices': allowed_choices,
    })
