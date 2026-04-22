from django.contrib import admin
from django.contrib import messages

from .models import ActionFeedItem, Badge, Clash, Season, SeasonArchive, UserBadge
from .tasks import archive_season


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_threshold')


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'awarded_at')


@admin.register(Clash)
class ClashAdmin(admin.ModelAdmin):
    list_display = ('name', 'department1', 'department2', 'start_date', 'end_date', 'is_active')
    list_filter = ('department1', 'department2')


@admin.action(description="Archive selected seasons (snapshot final standings into Hall of Fame)")
def archive_selected_seasons(modeladmin, request, queryset):
    count = 0
    for season in queryset:
        if not season.is_archived:
            archive_season.delay(season.id)
            count += 1
    messages.success(request, f"Queued {count} season(s) for archival.")


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active', 'is_archived')
    list_filter = ('is_archived',)
    actions = [archive_selected_seasons]


@admin.register(SeasonArchive)
class SeasonArchiveAdmin(admin.ModelAdmin):
    list_display = ('season', 'rank', 'user', 'final_score', 'department_name', 'archived_at')
    list_filter = ('season', 'department_name')
    search_fields = ('user__username', 'user__email')


@admin.register(ActionFeedItem)
class ActionFeedItemAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'user', 'message')
    list_filter = ('event_type',)
    search_fields = ('message', 'user__username')
    readonly_fields = ('created_at',)
