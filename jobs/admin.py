from django.contrib import admin
from .models import JobPosting


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'job_type', 'min_cgpa', 'deadline', 'status', 'is_open')
    list_filter = ('status', 'job_type', 'is_open', 'company')
    search_fields = ('title', 'company__name', 'description')
