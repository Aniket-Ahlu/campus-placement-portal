from django.urls import path
from . import views

app_name = 'placement_admin'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('companies/', views.pending_companies_queue, name='companies_queue'),
    path('companies/<int:pk>/moderate/', views.moderate_company, name='moderate_company'),
    path('postings/', views.pending_postings_queue, name='postings_queue'),
    path('postings/<int:pk>/', views.admin_posting_detail, name='posting_detail'),
    path('postings/<int:pk>/moderate/', views.moderate_posting, name='moderate_posting'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('users/', views.users_list, name='users_list'),
]
