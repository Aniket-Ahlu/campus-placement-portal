from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('companies/', include('companies.urls')),
    path('jobs/', include('jobs.urls')),
    path('applications/', include('applications.urls')),
    path('placement-admin/', include('placement_admin.urls')),
]

handler403 = 'core.views.error_403_view'
handler404 = 'core.views.error_404_view'
handler500 = 'core.views.error_500_view'
