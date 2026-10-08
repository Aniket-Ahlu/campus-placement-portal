from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('apply/<int:posting_id>/', views.apply_confirm, name='apply'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('<int:pk>/', views.application_detail, name='detail'),
    path('<int:pk>/withdraw/', views.withdraw_application, name='withdraw'),
    path('status-feed/', views.status_feed, name='status_feed'),
    path('posting/<int:posting_id>/applicants/', views.recruiter_posting_applicants, name='recruiter_applicants'),
    path('<int:pk>/recruiter-view/', views.recruiter_applicant_detail, name='recruiter_applicant_detail'),
]
