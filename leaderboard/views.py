import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from ingestion.models import ActivityLog
from scoring.models import Quest, ScoreLog, UserQuestProgress, UserStreak
from users.models import CustomUser

from .models import ActionFeedItem, Clash, Season, SeasonArchive


def _current_season():
    """Return the single currently-active Season, if any."""
    now = timezone.now()
    return Season.objects.filter(
        start_date__lte=now, end_date__gte=now, is_archived=False
    ).first()


def arena_view(request):
    """
    The Arena (Index View): A dynamic leaderboard table showing total points.
    Supports HTMX filters for 'all-time', 'season', and 'this-week'.
    """
    filter_mode = request.GET.get('filter', 'all_time')
    current_season = _current_season()
    now = timezone.now()

    base_qs = CustomUser.objects.all()

    if filter_mode == 'season' and current_season:
        users = base_qs.annotate(
            total_score=Sum(
                'score_logs__final_points',
                filter=Q(
                    score_logs__created_at__gte=current_season.start_date,
                    score_logs__created_at__lte=current_season.end_date,
                ),
            )
        ).order_by('-total_score')
    elif filter_mode == 'this_week':
        week_start = now - timedelta(days=7)
        users = base_qs.annotate(
            total_score=Sum(
                'score_logs__final_points',
                filter=Q(score_logs__created_at__gte=week_start),
            )
        ).order_by('-total_score')
    else:
        users = base_qs.annotate(
            total_score=Sum('score_logs__final_points')
        ).order_by('-total_score')

    active_clashes = Clash.objects.filter(start_date__lte=now, end_date__gte=now)
    clashes_data = []
    for clash in active_clashes:
        d1 = clash.dept1_score
        d2 = clash.dept2_score
        total = d1 + d2
        d1_pct = (d1 / total * 100) if total > 0 else 50
        clashes_data.append({
            'clash': clash,
            'd1_score': d1,
            'd2_score': d2,
            'd1_pct': d1_pct,
            'd2_pct': 100 - d1_pct,
        })

    context = {
        'users': users,
        'clashes_data': clashes_data,
        'current_season': current_season,
        'filter_mode': filter_mode,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'leaderboard/partials/arena_table.html', context)

    return render(request, 'leaderboard/arena.html', context)


def trophy_room_view(request, username):
    """The Trophy Room (Profile View): individual stats, badges, streaks and quests."""
    user = get_object_or_404(CustomUser, username=username)
    badges = user.badges.all()

    total_score = user.score_logs.aggregate(Sum('final_points'))['final_points__sum'] or 0
    score_logs = user.score_logs.all().order_by('-created_at')[:10]

    # Usage history over last 14 days
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    daily_scores = (
        user.score_logs.filter(created_at__gte=fourteen_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(daily_points=Sum('final_points'))
        .order_by('date')
    )

    dates, points = [], []
    for entry in daily_scores:
        dates.append(entry['date'].strftime('%b %d'))
        points.append(round(entry['daily_points'], 1))

    # Rival tracking logic
    rival = None
    rival_message = None
    if user.department:
        department_users = CustomUser.objects.filter(department=user.department).annotate(
            ts=Sum('score_logs__final_points')
        ).exclude(ts__isnull=True).order_by('ts')

        ts = total_score
        potential_rivals = [u for u in department_users if u.ts > ts and u.id != user.id]
        if potential_rivals:
            rival = potential_rivals[0]
            user_14d = sum([entry['daily_points'] for entry in daily_scores])
            rival_scores = (
                rival.score_logs.filter(created_at__gte=fourteen_days_ago)
                .aggregate(total=Sum('final_points'))['total']
                or 0
            )
            user_avg = user_14d / 14.0
            rival_avg = rival_scores / 14.0

            if user_avg > rival_avg + 0.1:
                days_to_pass = (rival.ts - ts) / (user_avg - rival_avg)
                rival_message = f"At your current pace, you'll overtake {rival.username} in {int(days_to_pass)+1} days! Keep prompting."
            else:
                rival_message = f"{rival.username} is maintaining their lead. Step up your game!"

    # Streak + Quest progress
    streak, _ = UserStreak.objects.get_or_create(user=user)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    quest_rows = []
    for quest in Quest.objects.filter(is_active=True).order_by('scope', 'name'):
        period_start = today if quest.scope == 'daily' else week_start
        progress = UserQuestProgress.objects.filter(
            user=user, quest=quest, period_start=period_start
        ).first()
        quest_rows.append({
            'quest': quest,
            'progress': progress,
            'current': progress.current_count if progress else 0,
            'pct': progress.progress_pct if progress else 0,
            'complete': bool(progress and progress.is_complete),
        })

    # Hall-of-fame finishes this user has collected
    archives = SeasonArchive.objects.filter(user=user).select_related('season').order_by('-season__end_date')[:5]

    context = {
        'profile_user': user,
        'badges': badges,
        'score_logs': score_logs,
        'total_score': total_score,
        'chart_labels': json.dumps(dates),
        'chart_data': json.dumps(points),
        'rival': rival,
        'rival_message': rival_message,
        'streak': streak,
        'quest_rows': quest_rows,
        'archives': archives,
    }
    return render(request, 'leaderboard/trophy_room.html', context)


@staff_member_required
def command_center_view(request):
    """Command Center (Admin Dashboard): aggregate events."""
    return render(request, 'leaderboard/command_center.html')


def stats_webhooks_view(request):
    total = ActivityLog.objects.count()
    return JsonResponse({'total': total})


def stats_copilots_view(request):
    active = ActivityLog.objects.filter(tool_name='github_copilot').values('user').distinct().count()
    return JsonResponse({'active': active})


def stats_flags_view(request):
    flags = ScoreLog.objects.filter(reason__icontains='Anti-cheat').count()
    return JsonResponse({'flags': flags})


def hall_of_fame_view(request):
    """List archived seasons with their top-3 podium."""
    archived_seasons = Season.objects.filter(is_archived=True).order_by('-end_date')
    seasons_data = []
    for season in archived_seasons:
        podium = SeasonArchive.objects.filter(season=season).select_related('user')[:3]
        seasons_data.append({'season': season, 'podium': podium})

    context = {
        'seasons_data': seasons_data,
        'current_season': _current_season(),
    }
    return render(request, 'leaderboard/hall_of_fame.html', context)


def season_detail_view(request, season_id):
    """Full archived leaderboard for one season."""
    season = get_object_or_404(Season, id=season_id)
    archives = SeasonArchive.objects.filter(season=season).select_related('user', 'user__department')
    context = {'season': season, 'archives': archives}
    return render(request, 'leaderboard/season_detail.html', context)


def feed_view(request):
    """HTMX polling target — returns the latest ticker items."""
    limit = int(request.GET.get('limit', 15))
    items = ActionFeedItem.objects.select_related('user').all()[:limit]
    context = {'items': items}
    return render(request, 'leaderboard/partials/action_ticker.html', context)
