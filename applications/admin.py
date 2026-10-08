from django.contrib import admin
from .models import Application, ApplicationStatusHistory


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'changed_at', 'note')
    can_delete = False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'posting', 'status', 'applied_at', 'updated_at')
    list_filter = ('status', 'posting__company')
    search_fields = ('student__username', 'posting__title')
    inlines = [ApplicationStatusHistoryInline]


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('application', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'changed_at')
    search_fields = ('application__student__username', 'application__posting__title')
