from django.contrib import admin
from .models import Badge, UserBadge, Clash

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
