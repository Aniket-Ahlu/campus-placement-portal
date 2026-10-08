from django.utils import timezone


def check_eligibility(profile, posting):
    """
    Evaluates whether a student profile meets all eligibility criteria for a job posting.
    Returns a list of human-readable failure reasons.
    If the list is empty, the student is fully eligible.
    """
    reasons = []

    # 1. Profile completeness
    if not profile or not profile.is_complete:
        missing = []
        if not profile:
            missing.append("profile")
        else:
            if not profile.full_name:
                missing.append("Full Name")
            if not profile.branch:
                missing.append("Branch")
            if profile.cgpa is None:
                missing.append("CGPA")
            if not profile.graduation_year:
                missing.append("Graduation Year")
            if not profile.resume_link:
                missing.append("Resume Link")
        reasons.append(f"Your profile is incomplete (missing: {', '.join(missing)}). Please complete your profile to apply.")

    # 2. CGPA Check
    if profile and profile.cgpa is not None:
        if profile.cgpa < posting.min_cgpa:
            reasons.append(
                f"You are not eligible: your CGPA is {profile.cgpa} but this role requires a minimum of {posting.min_cgpa}."
            )

    # 3. Branch Check (empty allowed_branches means all branches are eligible)
    if profile and profile.branch:
        allowed = list(posting.allowed_branches.all())
        if allowed and profile.branch not in allowed:
            allowed_names = ", ".join(b.name for b in allowed)
            reasons.append(
                f"Your branch ({profile.branch.name}) is not eligible for this role. Allowed branches: {allowed_names}."
            )

    # 4. Graduation Year Check (optional requirement on posting)
    if posting.graduation_year:
        if not profile or not profile.graduation_year or profile.graduation_year != posting.graduation_year:
            student_grad = profile.graduation_year if profile else "Unknown"
            reasons.append(
                f"This role is only open for {posting.graduation_year} graduates, but your graduation year is {student_grad}."
            )

    # 5. Application Deadline Check
    today = timezone.now().date()
    if posting.deadline < today:
        reasons.append(f"The application deadline ({posting.deadline}) has passed.")

    # 6. Posting Status & Company Status Check
    if not posting.is_open:
        reasons.append("Applications for this role are currently closed by the recruiter.")

    if posting.status != 'APPROVED' or posting.company.status != 'APPROVED':
        reasons.append("This posting is not currently accepting applications.")

    # 7. Duplicate Application Check
    if profile and profile.user_id:
        from applications.models import Application
        if Application.objects.filter(student_id=profile.user_id, posting=posting).exists():
            reasons.append("You have already applied to this posting.")

    return reasons
