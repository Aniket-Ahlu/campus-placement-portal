from django.conf import settings
from django.db import models


class AdminActionLog(models.Model):
    ACTION_APPROVED = 'APPROVED'
    ACTION_REJECTED = 'REJECTED'

    ACTION_CHOICES = [
        (ACTION_APPROVED, 'Approved'),
        (ACTION_REJECTED, 'Rejected'),
    ]

    TARGET_COMPANY = 'Company'
    TARGET_JOB_POSTING = 'JobPosting'

    TARGET_TYPE_CHOICES = [
        (TARGET_COMPANY, 'Company'),
        (TARGET_JOB_POSTING, 'Job Posting'),
    ]

    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_actions',
        verbose_name='Admin Account'
    )
    admin_id = models.IntegerField(null=True, blank=True, help_text="Snapshot ID of admin")
    admin_username = models.CharField(max_length=150, help_text="Snapshot username of admin")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, choices=TARGET_TYPE_CHOICES)
    target_id = models.IntegerField()
    target_label = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Admin Action Log'
        verbose_name_plural = 'Admin Action Logs'

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.admin_username} {self.action} {self.target_type} #{self.target_id} ({self.target_label})"

    @property
    def admin(self):
        return self.admin_user

    @admin.setter
    def admin(self, value):
        self.admin_user = value
