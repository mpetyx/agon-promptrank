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
