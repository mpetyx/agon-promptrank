from django.urls import path

from .views import roi_dashboard_view

app_name = 'analytics'

urlpatterns = [
    path('roi/', roi_dashboard_view, name='roi_dashboard'),
]
