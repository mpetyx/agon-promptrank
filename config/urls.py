"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import include, path

import leaderboard.views
from ingestion.views import DynamicIngestionWebhookView, IngestionWebhookView
from leaderboard.views import (
    arena_view,
    command_center_view,
    feed_view,
    hall_of_fame_view,
    season_detail_view,
    trophy_room_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', arena_view, name='arena'),
    path('u/<str:username>/', trophy_room_view, name='trophy_room'),
    path('command-center/', command_center_view, name='command_center'),
    path('hall-of-fame/', hall_of_fame_view, name='hall_of_fame'),
    path('hall-of-fame/<int:season_id>/', season_detail_view, name='season_detail'),
    path('api/feed/', feed_view, name='feed_poll'),
    path('api/stats/webhooks', leaderboard.views.stats_webhooks_view, name='stats_webhooks'),
    path('api/stats/copilots', leaderboard.views.stats_copilots_view, name='stats_copilots'),
    path('api/stats/flags', leaderboard.views.stats_flags_view, name='stats_flags'),
    path('api/v1/ingest/', IngestionWebhookView.as_view(), name='api_ingest'),
    path('api/v1/ingest/<slug:slug>/', DynamicIngestionWebhookView.as_view(), name='api_ingest_dynamic'),
    path('analytics/', include('analytics.urls', namespace='analytics')),
]
