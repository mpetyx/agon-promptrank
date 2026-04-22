from django.contrib import admin

from .models import Quest, ScoreLog, UserQuestProgress, UserStreak


@admin.register(ScoreLog)
class ScoreLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'final_points', 'multiplier_applied', 'reason', 'created_at')
    list_filter = ('reason',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'tool_name', 'action_type', 'target_count', 'reward_points', 'is_active')
    list_filter = ('scope', 'is_active', 'tool_name')


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_streak', 'longest_streak', 'last_active_date')
    search_fields = ('user__username',)


@admin.register(UserQuestProgress)
class UserQuestProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'quest', 'period_start', 'current_count', 'completed_at')
    list_filter = ('quest', 'period_start')
    search_fields = ('user__username', 'quest__name')
