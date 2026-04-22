"""Celery tasks for leaderboard lifecycle events — season archival + feed item generation."""
from celery import shared_task
from django.db.models import Q, Sum
from django.utils import timezone

from .models import ActionFeedItem, Season, SeasonArchive


@shared_task
def archive_ended_seasons():
    """Periodic task. Snapshots the final standings of any ended-but-not-archived season."""
    ended = Season.objects.filter(is_archived=False, end_date__lt=timezone.now())
    archived_names = []
    for season in ended:
        _archive_season(season)
        archived_names.append(season.name)
    return f"Archived {len(archived_names)} season(s): {archived_names}"


@shared_task
def archive_season(season_id):
    """Manually archive a single season by id (admin action)."""
    try:
        season = Season.objects.get(id=season_id)
    except Season.DoesNotExist:
        return f"Season {season_id} not found."
    _archive_season(season)
    return f"Archived {season.name}."


def _archive_season(season: Season):
    """Freeze a Season's leaderboard into SeasonArchive rows and publish a feed item."""
    from users.models import CustomUser

    if season.is_archived:
        return

    scored_users = CustomUser.objects.annotate(
        season_score=Sum(
            'score_logs__final_points',
            filter=Q(
                score_logs__created_at__gte=season.start_date,
                score_logs__created_at__lte=season.end_date,
            ),
        )
    ).exclude(season_score__isnull=True).order_by('-season_score')

    SeasonArchive.objects.filter(season=season).delete()
    for rank, user in enumerate(scored_users, start=1):
        SeasonArchive.objects.create(
            season=season,
            user=user,
            rank=rank,
            final_score=round(user.season_score or 0.0, 2),
            department_name=user.department.name if user.department else '',
        )
        if rank == 1:
            ActionFeedItem.objects.create(
                user=user,
                event_type='season',
                icon='👑',
                message=f"{user.username} crowned champion of {season.name}!",
            )

    season.is_archived = True
    season.save(update_fields=['is_archived'])


@shared_task
def publish_feed_item(user_id, event_type, message, icon='⚡'):
    """Lightweight shim so other apps can enqueue ticker items without importing leaderboard directly."""
    from users.models import CustomUser
    user = None
    if user_id:
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            pass
    ActionFeedItem.objects.create(
        user=user,
        event_type=event_type,
        message=message[:255],
        icon=icon[:10] or '⚡',
    )
    return f"Feed: {event_type} — {message[:60]}"
