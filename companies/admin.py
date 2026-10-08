from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'industry', 'location', 'status', 'created_at')
    list_filter = ('status', 'industry')
    search_fields = ('name', 'owner__username', 'industry', 'location')
