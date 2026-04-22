"""ROI / Cost dashboards — business justification for AI tooling spend."""
import json
from collections import defaultdict
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from ingestion.models import ActivityLog
from scoring.models import ScoreLog
from users.models import Department

from .models import ToolCost


@staff_member_required
def roi_dashboard_view(request):
    """
    Aggregates ActivityLog volume × ToolCost configuration to estimate ROI.

    Produces:
      - totals: monthly_cost, estimated_value, net_value, roi_pct
      - per_tool: breakdown rows for the table
      - per_department: rows showing spend-vs-value across the org
      - chart_cost / chart_value arrays for Chart.js
      - trend series: last 30 days of daily value generated
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)

    tool_counts = (
        ActivityLog.objects.filter(created_at__gte=thirty_days_ago)
        .values('tool_name')
        .annotate(actions=Count('id'), active_users=Count('user', distinct=True))
        .order_by('-actions')
    )
    counts_by_tool = {row['tool_name']: row for row in tool_counts}

    active_costs = ToolCost.objects.filter(is_active=True)

    per_tool = []
    total_cost = 0.0
    total_value = 0.0
    for cost in active_costs:
        row = counts_by_tool.get(cost.tool_name, {'actions': 0, 'active_users': 0})
        actions = row['actions']
        active_users = row['active_users']
        monthly_cost = cost.monthly_cost_per_seat_usd * active_users
        value_generated = cost.value_per_action_usd * actions
        net = value_generated - monthly_cost
        roi_pct = ((value_generated - monthly_cost) / monthly_cost * 100) if monthly_cost else None
        per_tool.append({
            'cost': cost,
            'actions': actions,
            'active_users': active_users,
            'monthly_cost': round(monthly_cost, 2),
            'value_generated': round(value_generated, 2),
            'net_value': round(net, 2),
            'roi_pct': round(roi_pct, 1) if roi_pct is not None else None,
        })
        total_cost += monthly_cost
        total_value += value_generated

    per_tool.sort(key=lambda r: r['net_value'], reverse=True)

    net_value = total_value - total_cost
    overall_roi = ((net_value) / total_cost * 100) if total_cost else None

    # Per-department breakdown: value = Σ minutes_saved_per_action × hourly_rate × action count
    minutes_by_tool = {c.tool_name: c.minutes_saved_per_action for c in active_costs}
    hourly_by_tool = {c.tool_name: c.avg_hourly_rate_usd for c in active_costs}

    dept_activity = (
        ActivityLog.objects.filter(
            created_at__gte=thirty_days_ago,
            user__isnull=False,
            user__department__isnull=False,
        )
        .values('user__department__name', 'tool_name')
        .annotate(actions=Count('id'))
    )
    dept_totals = defaultdict(lambda: {'value': 0.0, 'actions': 0})
    for row in dept_activity:
        dept_name = row['user__department__name']
        tool = row['tool_name']
        actions = row['actions']
        minutes = minutes_by_tool.get(tool, 0)
        hourly = hourly_by_tool.get(tool, 0)
        value = (minutes / 60.0) * hourly * actions
        dept_totals[dept_name]['value'] += value
        dept_totals[dept_name]['actions'] += actions

    per_department = sorted(
        [
            {
                'department': name,
                'actions': stats['actions'],
                'value_generated': round(stats['value'], 2),
            }
            for name, stats in dept_totals.items()
        ],
        key=lambda r: r['value_generated'],
        reverse=True,
    )

    # 30-day trend of estimated value
    from django.db.models.functions import TruncDate

    daily = (
        ActivityLog.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day', 'tool_name')
        .annotate(actions=Count('id'))
        .order_by('day')
    )
    by_day = defaultdict(float)
    for row in daily:
        minutes = minutes_by_tool.get(row['tool_name'], 0)
        hourly = hourly_by_tool.get(row['tool_name'], 0)
        by_day[row['day']] += (minutes / 60.0) * hourly * row['actions']

    trend_labels = [d.strftime('%b %d') for d in sorted(by_day.keys())]
    trend_values = [round(by_day[d], 2) for d in sorted(by_day.keys())]

    # Chart arrays for cost-vs-value bars per tool
    chart_tool_labels = [r['cost'].display_name for r in per_tool]
    chart_cost = [r['monthly_cost'] for r in per_tool]
    chart_value = [r['value_generated'] for r in per_tool]

    # Hours saved summary (everyone loves the number)
    total_minutes_saved = 0.0
    for tool_name, minutes in minutes_by_tool.items():
        row = counts_by_tool.get(tool_name)
        if row:
            total_minutes_saved += minutes * row['actions']
    total_hours_saved = total_minutes_saved / 60.0

    context = {
        'per_tool': per_tool,
        'per_department': per_department,
        'total_cost': round(total_cost, 2),
        'total_value': round(total_value, 2),
        'net_value': round(net_value, 2),
        'overall_roi': round(overall_roi, 1) if overall_roi is not None else None,
        'total_hours_saved': round(total_hours_saved, 1),
        'chart_tool_labels': json.dumps(chart_tool_labels),
        'chart_cost': json.dumps(chart_cost),
        'chart_value': json.dumps(chart_value),
        'trend_labels': json.dumps(trend_labels),
        'trend_values': json.dumps(trend_values),
        'has_costs_configured': active_costs.exists(),
    }
    return render(request, 'analytics/roi_dashboard.html', context)
