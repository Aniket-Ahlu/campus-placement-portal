from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('profile/', views.company_profile, name='profile'),
]
