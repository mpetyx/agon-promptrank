from datetime import date, timedelta

from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from ingestion.models import ActivityLog
from leaderboard.models import ActionFeedItem, Badge, UserBadge
from scoring.models import Quest, ScoreLog, UserQuestProgress, UserStreak


# Points at which we want to shout out a user in the ticker.
POINT_MILESTONES = [10, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

# Streak day-counts worth calling out.
STREAK_MILESTONES = [3, 7, 14, 30, 60, 100]


@shared_task
def process_activity_log(activity_log_id):
    """
    Core anti-cheat engine. Processes a raw ActivityLog into ScoreLog.
    Applies department handicaps, rate-limiting, streak tracking, and quest progress.
    """
    try:
        log = ActivityLog.objects.get(id=activity_log_id)
    except ActivityLog.DoesNotExist:
        return f"ActivityLog {activity_log_id} not found."

    if log.processed:
        return f"ActivityLog {activity_log_id} already processed."

    if not log.user:
        log.processed = True
        log.save()
        return "No user associated. Ignored."

    base_points = log.value_metric
    user = log.user

    # 1. Anti-Cheat: Rate limiting / Spam deduction
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_count = ActivityLog.objects.filter(
        user=user,
        tool_name=log.tool_name,
        created_at__gte=one_minute_ago,
    ).count()

    reason = "Standard processing."
    if recent_count > 10:
        base_points = base_points * 0.1
        reason = "Anti-cheat rate-limiting applied. Spamming detected."

    # 2. Handicap application
    multiplier = user.department.handicap_multiplier if user.department else 1.0
    final_points = base_points * multiplier

    # 3. Save ScoreLog
    score_log = ScoreLog.objects.create(
        user=user,
        activity_log=log,
        base_points=base_points,
        multiplier_applied=multiplier,
        final_points=final_points,
        reason=reason,
    )

    log.processed = True
    log.save()

    # 4. Fan out async work: streaks, quests, badges, milestones.
    update_streak.delay(user.id)
    update_quest_progress.delay(user.id, log.id)
    check_and_award_badges.delay(user.id)
    check_point_milestones.delay(user.id, float(final_points))

    return f"Processed ScoreLog {score_log.id} for ActivityLog {activity_log_id} with points {final_points}."


@shared_task
def check_and_award_badges(user_id):
    """Checks if the user has crossed thresholds for new trophies."""
    from users.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return

    total_score = user.score_logs.aggregate(Sum('final_points'))['final_points__sum'] or 0

    eligible_badges = Badge.objects.filter(points_threshold__lte=total_score).exclude(
        id__in=user.badges.values_list('badge_id', flat=True)
    )

    for badge in eligible_badges:
        UserBadge.objects.create(user=user, badge=badge)

        from notifications.services import format_badge_message, send_slack_notification
        msg = format_badge_message(user, badge)
        send_slack_notification(msg)

        ActionFeedItem.objects.create(
            user=user,
            event_type='badge',
            icon=(badge.icon_svg or '🏆')[:10],
            message=f"{user.username} unlocked the '{badge.name}' badge!",
        )

    return f"Checked badges for user {user_id}."


@shared_task
def update_streak(user_id):
    """Increments or resets a user's consecutive-day streak based on today's activity."""
    from users.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return

    today = timezone.localdate()
    streak, _ = UserStreak.objects.get_or_create(user=user)

    if streak.last_active_date == today:
        return "Already counted today."

    if streak.last_active_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    streak.last_active_date = today
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak
    streak.save()

    if streak.current_streak in STREAK_MILESTONES:
        ActionFeedItem.objects.create(
            user=user,
            event_type='streak',
            icon='🔥',
            message=f"{user.username} is on a {streak.current_streak}-day streak!",
        )

    return f"Streak for {user.username}: {streak.current_streak}"


@shared_task
def update_quest_progress(user_id, activity_log_id):
    """Advance any active quests that match this activity's tool/action."""
    from users.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)
        log = ActivityLog.objects.get(id=activity_log_id)
    except (CustomUser.DoesNotExist, ActivityLog.DoesNotExist):
        return

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())  # Monday

    active_quests = Quest.objects.filter(is_active=True)
    completed_now = []

    for quest in active_quests:
        if quest.tool_name and quest.tool_name != log.tool_name:
            continue
        if quest.action_type and quest.action_type != log.action_type:
            continue

        period_start = today if quest.scope == 'daily' else week_start

        progress, created = UserQuestProgress.objects.get_or_create(
            user=user,
            quest=quest,
            period_start=period_start,
            defaults={'current_count': 0},
        )

        if progress.is_complete:
            continue

        progress.current_count += 1

        if progress.current_count >= quest.target_count:
            progress.completed_at = timezone.now()
            progress.save()
            completed_now.append((quest, progress))

            # Grant reward by creating a ScoreLog without an ActivityLog tether.
            # We use the triggering log so we have a back-reference, but we build
            # a synthetic one-off entry instead (so anti-cheat doesn't double-count).
            _award_quest_reward(user, quest)

            ActionFeedItem.objects.create(
                user=user,
                event_type='quest',
                icon=quest.icon or '🎯',
                message=f"{user.username} completed the '{quest.name}' quest!",
            )
        else:
            progress.save()

    return f"Updated {active_quests.count()} quests for user {user_id}, completed {len(completed_now)}."


def _award_quest_reward(user, quest):
    """Create a synthetic ActivityLog + ScoreLog so the reward shows up in history."""
    synthetic = ActivityLog.objects.create(
        tool_name='agon_quest',
        user_email=user.email,
        user=user,
        action_type=f'quest_reward:{quest.name}',
        value_metric=quest.reward_points,
        raw_payload={'quest_id': quest.id, 'quest_name': quest.name},
        processed=True,
    )
    ScoreLog.objects.create(
        user=user,
        activity_log=synthetic,
        base_points=quest.reward_points,
        multiplier_applied=1.0,
        final_points=quest.reward_points,
        reason=f"Quest reward: {quest.name}",
    )


@shared_task
def check_point_milestones(user_id, just_awarded):
    """Emit a ticker item when a user crosses a round total-points milestone."""
    from users.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return

    new_total = user.score_logs.aggregate(Sum('final_points'))['final_points__sum'] or 0
    old_total = new_total - just_awarded

    crossed = [m for m in POINT_MILESTONES if old_total < m <= new_total]
    for milestone in crossed:
        ActionFeedItem.objects.create(
            user=user,
            event_type='milestone',
            icon='💎',
            message=f"{user.username} blew past {milestone:g} points!",
        )
    return f"Crossed milestones: {crossed}"


@shared_task
def reset_expired_quest_progress():
    """Optional sweep to purge stale progress rows (kept for housekeeping; UI filters by period_start anyway)."""
    cutoff = timezone.localdate() - timedelta(days=60)
    deleted, _ = UserQuestProgress.objects.filter(period_start__lt=cutoff).delete()
    return f"Pruned {deleted} stale quest progress rows."
