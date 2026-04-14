from django.shortcuts import render, get_object_or_404
from users.models import CustomUser
from scoring.models import ScoreLog
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
import json
from .models import Clash

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
    
    now = timezone.now()
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
            'd2_pct': 100 - d1_pct
        })
    
    context = {
        'users': users,
        'clashes_data': clashes_data
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'leaderboard/partials/arena_table.html', context)
        
    return render(request, 'leaderboard/arena.html', context)



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

    # Rival tracking logic
    rival = None
    rival_message = None
    if user.department:
        # Find the immediate next user in score in the same department
        department_users = CustomUser.objects.filter(department=user.department).annotate(
            ts=Sum('score_logs__final_points')
        ).exclude(ts__isnull=True).order_by('ts')
        
        # User's total_score might be handled differently, let's make sure it handles None
        ts = total_score
        potential_rivals = [u for u in department_users if u.ts > ts and u.id != user.id]
        if potential_rivals:
            rival = potential_rivals[0] # The one slightly above
            
            # Predict
            user_14d = sum([entry['daily_points'] for entry in daily_scores])
            rival_scores = rival.score_logs.filter(created_at__gte=fourteen_days_ago) \
                .aggregate(total=Sum('final_points'))['total'] or 0
                
            user_avg = user_14d / 14.0
            rival_avg = rival_scores / 14.0
            
            if user_avg > rival_avg + 0.1: # Must be gaining at least 0.1 point per day
                days_to_pass = (rival.ts - ts) / (user_avg - rival_avg)
                rival_message = f"At your current pace, you'll overtake {rival.username} in {int(days_to_pass)+1} days! Keep prompting."
            else:
                rival_message = f"{rival.username} is maintaining their lead. Step up your game!"

    context = {
        'profile_user': user,
        'badges': badges,
        'score_logs': score_logs,
        'total_score': total_score,
        'chart_labels': json.dumps(dates),
        'chart_data': json.dumps(points),
        'rival': rival,
        'rival_message': rival_message,
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
