from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class JobPosting(models.Model):
    JOB_TYPE_FULLTIME = 'JOB'
    JOB_TYPE_INTERNSHIP = 'INTERNSHIP'

    JOB_TYPE_CHOICES = [
        (JOB_TYPE_FULLTIME, 'Full-time Job'),
        (JOB_TYPE_INTERNSHIP, 'Internship'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='postings'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default=JOB_TYPE_FULLTIME)
    location = models.CharField(max_length=200)
    salary_or_stipend = models.CharField(max_length=150, help_text="e.g. 12 LPA or ₹30,000/month")
    min_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )
    allowed_branches = models.ManyToManyField('core.Branch', blank=True, related_name='job_postings')
    graduation_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Target graduation year (leave blank if open to all batches)"
    )
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} at {self.company.name}"

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def is_active(self):
        return (
            self.status == self.STATUS_APPROVED
            and self.company.status == 'APPROVED'
            and self.is_open
            and self.deadline >= timezone.now().date()
        )
