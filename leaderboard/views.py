from django.shortcuts import render, get_object_or_404
from users.models import CustomUser
from scoring.models import ScoreLog
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required

def arena_view(request):
    """
    The Arena (Index View): A dynamic leaderboard table showing total points.
    Includes HTMX filters to sort by Time and Department.
    """
    users = CustomUser.objects.annotate(
        total_score=Sum('score_logs__final_points')
    ).order_by('-total_score')

    # Basic HTMX filtering can be handled here if requested.
    # e.g., if request.htmx and request.GET.get('filter') == 'this_week'
    
    context = {
        'users': users
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'leaderboard/partials/arena_table.html', context)
        
    return render(request, 'leaderboard/arena.html', context)

from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
import json

def trophy_room_view(request, username):
    """
    The Trophy Room (Profile View): Individual stats and Badge models.
    """
    user = get_object_or_404(CustomUser, username=username)
    badges = user.badges.all()
    
    # We want ALL logs for total score, but recent 10 for the list. Wait, 
    # previously total_score was calculated off the slice [:10] by accident! Left's fix that.
    total_score = user.score_logs.aggregate(Sum('final_points'))['final_points__sum'] or 0
    score_logs = user.score_logs.all().order_by('-created_at')[:10]

    # Usage history over last 14 days
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    daily_scores = user.score_logs.filter(created_at__gte=fourteen_days_ago) \
        .annotate(date=TruncDate('created_at')) \
        .values('date') \
        .annotate(daily_points=Sum('final_points')) \
        .order_by('date')
    
    dates = []
    points = []
    for entry in daily_scores:
        dates.append(entry['date'].strftime('%b %d'))
        points.append(round(entry['daily_points'], 1))

    context = {
        'profile_user': user,
        'badges': badges,
        'score_logs': score_logs,
        'total_score': total_score,
        'chart_labels': json.dumps(dates),
        'chart_data': json.dumps(points),
    }
    return render(request, 'leaderboard/trophy_room.html', context)

from django.http import JsonResponse
from ingestion.models import ActivityLog
from scoring.models import ScoreLog

@staff_member_required
def command_center_view(request):
    """
    Command Center (Admin Dashboard): aggregate events.
    """
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
