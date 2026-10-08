from django.conf import settings
from django.db import models


class Application(models.Model):
    STATUS_APPLIED = 'APPLIED'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_SHORTLISTED = 'SHORTLISTED'
    STATUS_INTERVIEW = 'INTERVIEW'
    STATUS_OFFERED = 'OFFERED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_WITHDRAWN = 'WITHDRAWN'

    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_SHORTLISTED, 'Shortlisted'),
        (STATUS_INTERVIEW, 'Interview Scheduled'),
        (STATUS_OFFERED, 'Offer Extended'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]

    FINAL_STATUSES = {STATUS_OFFERED, STATUS_REJECTED, STATUS_WITHDRAWN}

    # Recruiter transitions: non-final to next step or REJECTED
    ALLOWED_RECRUITER_TRANSITIONS = {
        STATUS_APPLIED: [STATUS_UNDER_REVIEW, STATUS_REJECTED],
        STATUS_UNDER_REVIEW: [STATUS_SHORTLISTED, STATUS_REJECTED],
        STATUS_SHORTLISTED: [STATUS_INTERVIEW, STATUS_REJECTED],
        STATUS_INTERVIEW: [STATUS_OFFERED, STATUS_REJECTED],
        STATUS_OFFERED: [],
        STATUS_REJECTED: [],
        STATUS_WITHDRAWN: [],
    }

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    posting = models.ForeignKey(
        'jobs.JobPosting',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recruiter_note = models.TextField(blank=True)

    class Meta:
        unique_together = ('student', 'posting')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student.username} - {self.posting.title} ({self.get_status_display()})"

    @property
    def is_final(self):
        return self.status in self.FINAL_STATUSES

    @property
    def can_withdraw(self):
        return not self.is_final

    @property
    def badge_class(self):
        mapping = {
            self.STATUS_APPLIED: 'bg-secondary',
            self.STATUS_UNDER_REVIEW: 'bg-warning text-dark',
            self.STATUS_SHORTLISTED: 'bg-info text-dark',
            self.STATUS_INTERVIEW: 'bg-primary',
            self.STATUS_OFFERED: 'bg-success',
            self.STATUS_REJECTED: 'bg-danger',
            self.STATUS_WITHDRAWN: 'bg-dark',
        }
        return mapping.get(self.status, 'bg-secondary')

    def can_transition_to(self, new_status, by_user):
        if self.is_final:
            return False, f"Application is in final state '{self.get_status_display()}' and cannot be updated."

        if by_user.is_student:
            if new_status == self.STATUS_WITHDRAWN:
                return True, ""
            return False, "Students can only withdraw an active application."

        if by_user.is_recruiter or by_user.is_placement_admin:
            allowed = self.ALLOWED_RECRUITER_TRANSITIONS.get(self.status, [])
            if new_status in allowed:
                return True, ""
            return False, f"Transition from '{self.get_status_display()}' to '{dict(self.STATUS_CHOICES).get(new_status, new_status)}' is not allowed."

        return False, "Unauthorized to change status."


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changes'
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['changed_at']

    def __str__(self):
        return f"{self.application_id}: {self.old_status} -> {self.new_status} at {self.changed_at}"
