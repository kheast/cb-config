"""
URL configuration for cbconfig project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
]
