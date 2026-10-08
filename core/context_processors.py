def portal_context(request):
    """
    Exposes common context information across templates.
    """
    ctx = {
        'current_role': None,
        'user_company': None,
        'has_approved_company': False,
        'student_profile': None,
        'pending_admin_count': 0,
    }

    user = request.user
    if user.is_authenticated:
        ctx['current_role'] = user.role
        if user.is_recruiter:
            company = user.companies.first()
            ctx['user_company'] = company
            ctx['has_approved_company'] = bool(company and company.status == 'APPROVED')
        elif user.is_student:
            if hasattr(user, 'student_profile'):
                ctx['student_profile'] = user.student_profile
        elif user.is_placement_admin:
            from companies.models import Company
            from jobs.models import JobPosting
            ctx['pending_admin_count'] = (
                Company.objects.filter(status='PENDING').count() +
                JobPosting.objects.filter(status='PENDING').count()
            )

    return ctx
