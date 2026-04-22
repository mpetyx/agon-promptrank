from django.contrib import admin
from .models import ToolCost


@admin.register(ToolCost)
class ToolCostAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'tool_name', 'monthly_cost_per_seat_usd', 'minutes_saved_per_action', 'avg_hourly_rate_usd', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('tool_name', 'display_name')
