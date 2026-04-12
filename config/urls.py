"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
import leaderboard.views
from leaderboard.views import arena_view, trophy_room_view, command_center_view
from ingestion.views import IngestionWebhookView, DynamicIngestionWebhookView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', arena_view, name='arena'),
    path('u/<str:username>/', trophy_room_view, name='trophy_room'),
    path('command-center/', command_center_view, name='command_center'),
    path('api/stats/webhooks', leaderboard.views.stats_webhooks_view, name='stats_webhooks'),
    path('api/stats/copilots', leaderboard.views.stats_copilots_view, name='stats_copilots'),
    path('api/stats/flags', leaderboard.views.stats_flags_view, name='stats_flags'),
    path('api/v1/ingest/', IngestionWebhookView.as_view(), name='api_ingest'),
    path('api/v1/ingest/<slug:slug>/', DynamicIngestionWebhookView.as_view(), name='api_ingest_dynamic'),
]
