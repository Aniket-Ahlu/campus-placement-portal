from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.db import models


class User(AbstractUser):
    ROLE_STUDENT = 'STUDENT'
    ROLE_RECRUITER = 'RECRUITER'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_RECRUITER, 'Recruiter'),
        (ROLE_ADMIN, 'Placement Admin'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_recruiter(self):
        return self.role == self.ROLE_RECRUITER

    @property
    def is_placement_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=150, blank=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="CGPA on a scale of 0.00 to 10.00"
    )
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    resume_link = models.URLField(max_length=500, blank=True, validators=[URLValidator()])
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def is_complete(self):
        return bool(
            self.full_name
            and self.branch
            and (self.cgpa is not None)
            and self.graduation_year
            and self.resume_link
        )

    @property
    def completion_percentage(self):
        fields = [
            bool(self.full_name),
            bool(self.branch),
            self.cgpa is not None,
            bool(self.graduation_year),
            bool(self.resume_link),
            bool(self.phone),
        ]
        return int((sum(1 for f in fields if f) / len(fields)) * 100)
