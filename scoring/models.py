from django.db import models
from users.models import CustomUser
from ingestion.models import ActivityLog

class ScoreLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='score_logs')
    activity_log = models.OneToOneField(ActivityLog, on_delete=models.CASCADE, related_name='score')
    base_points = models.FloatField()
    multiplier_applied = models.FloatField()
    final_points = models.FloatField()
    reason = models.CharField(max_length=255, blank=True, help_text="Reason for specific point calculation, like anti-cheat limits.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"+{self.final_points} for {self.user} from {self.activity_log.tool_name}"


class UserStreak(models.Model):
    """Tracks consecutive-day AI tool usage per user."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}: {self.current_streak} day streak (best: {self.longest_streak})"


class Quest(models.Model):
    """Daily or weekly challenges — 'Generate 10 Copilot completions today'."""
    SCOPE_CHOICES = [('daily', 'Daily'), ('weekly', 'Weekly')]

    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    tool_name = models.CharField(max_length=100, blank=True, help_text="Optional — limits quest to a specific tool (e.g. 'github_copilot'). Blank = any tool.")
    action_type = models.CharField(max_length=100, blank=True, help_text="Optional — limits quest to an action type.")
    target_count = models.PositiveIntegerField(default=5)
    reward_points = models.FloatField(default=5.0)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='daily')
    icon = models.CharField(max_length=10, blank=True, default='🎯')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.scope}, target {self.target_count})"


class UserQuestProgress(models.Model):
    """Tracks progress on a quest for a given period (day or ISO-week start)."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='quest_progress')
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='progress_entries')
    period_start = models.DateField(help_text="Day (daily quests) or Monday of ISO week (weekly quests).")
    current_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'quest', 'period_start')
        ordering = ['-period_start']

    @property
    def is_complete(self):
        return self.completed_at is not None

    @property
    def progress_pct(self):
        if not self.quest.target_count:
            return 0
        return min(100, int((self.current_count / self.quest.target_count) * 100))

    def __str__(self):
        state = "✅" if self.is_complete else f"{self.current_count}/{self.quest.target_count}"
        return f"{self.user.username} — {self.quest.name} [{state}]"
