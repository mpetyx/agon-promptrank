from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from ingestion.models import ActivityLog
from scoring.models import ScoreLog
from leaderboard.models import Badge, UserBadge
from django.db.models import Sum

@shared_task
def process_activity_log(activity_log_id):
    """
    Core anti-cheat engine. Processes a raw ActivityLog into ScoreLog.
    Applies department handicaps and rate-limiting limits.
    """
    try:
        log = ActivityLog.objects.get(id=activity_log_id)
    except ActivityLog.DoesNotExist:
        return f"ActivityLog {activity_log_id} not found."
        
    if log.processed:
        return f"ActivityLog {activity_log_id} already processed."
        
    if not log.user:
        # Can't score an unregistered user
        log.processed = True
        log.save()
        return "No user associated. Ignored."
        
    base_points = log.value_metric
    user = log.user
    
    # 1. Anti-Cheat: Rate limiting / Spammage deduction
    # If the user has submitted more than 10 fast-fire requests in the last minute
    # for the same tool, we start depreciating the points.
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_count = ActivityLog.objects.filter(
        user=user, 
        tool_name=log.tool_name, 
        created_at__gte=one_minute_ago
    ).count()
    
    reason = "Standard processing."
    if recent_count > 10:
        base_points = base_points * 0.1  # Heavy throttle for spam
        reason = "Anti-cheat rate-limiting applied. Spamming detected."

    # 2. Handicap application
    multiplier = user.department.handicap_multiplier if user.department else 1.0
    final_points = base_points * multiplier
    
    # 3. Save ScoreLog
    ScoreLog.objects.create(
        user=user,
        activity_log=log,
        base_points=base_points,
        multiplier_applied=multiplier,
        final_points=final_points,
        reason=reason
    )
    
    log.processed = True
    log.save()
    
    # 4. Check for thresholds to award new Badges asynchronously
    check_and_award_badges.delay(user.id)
    
    return f"Processed ScoreLog for ActivityLog {activity_log_id} with points {final_points}."

@shared_task
def check_and_award_badges(user_id):
    """Checks if the user has crossed thresholds for new trophies."""
    from users.models import CustomUser
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return
        
    total_score = user.score_logs.aggregate(Sum('final_points'))['final_points__sum'] or 0
    
    # Find badges the user doesn't have yet, where their score is >= threshold
    eligible_badges = Badge.objects.filter(points_threshold__lte=total_score).exclude(
        id__in=user.badges.values_list('badge_id', flat=True)
    )
    
    for badge in eligible_badges:
        UserBadge.objects.create(user=user, badge=badge)
        
        # Trigger outbound webhook
        from notifications.services import send_slack_notification, format_badge_message
        msg = format_badge_message(user, badge)
        send_slack_notification(msg)
        
    return f"Checked badges for user {user_id}."
