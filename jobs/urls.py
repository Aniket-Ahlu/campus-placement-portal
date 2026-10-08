from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.browse_postings, name='browse'),
    path('<int:pk>/', views.posting_detail, name='detail'),
    path('recruiter/dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('recruiter/postings/', views.recruiter_postings_list, name='recruiter_postings'),
    path('recruiter/postings/create/', views.recruiter_posting_create, name='recruiter_posting_create'),
    path('recruiter/postings/<int:pk>/edit/', views.recruiter_posting_edit, name='recruiter_posting_edit'),
    path('recruiter/postings/<int:pk>/toggle/', views.recruiter_posting_toggle, name='recruiter_posting_toggle'),
]
