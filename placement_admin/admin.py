from django.contrib import admin
from .models import AdminActionLog


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'admin_username', 'action', 'target_type', 'target_id', 'target_label')
    list_filter = ('action', 'target_type', 'timestamp')
    search_fields = ('admin_username', 'target_label', 'reason')
    readonly_fields = [f.name for f in AdminActionLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
