from django.db import models


class ToolCost(models.Model):
    """Finance inputs so managers can see cost-vs-value ROI for each AI tool."""
    tool_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Must match the tool_name recorded on ActivityLog (e.g. 'github_copilot').",
    )
    display_name = models.CharField(max_length=120, help_text="Friendly name for dashboards. Ex: 'GitHub Copilot Enterprise'.")
    monthly_cost_per_seat_usd = models.FloatField(default=0.0, help_text="Per-seat subscription cost.")
    minutes_saved_per_action = models.FloatField(default=2.0, help_text="Estimated minutes of developer time each action saves.")
    avg_hourly_rate_usd = models.FloatField(default=80.0, help_text="Blended hourly rate used to translate time saved into dollars.")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.display_name} (${self.monthly_cost_per_seat_usd}/seat/mo)"

    @property
    def value_per_action_usd(self):
        return (self.minutes_saved_per_action / 60.0) * self.avg_hourly_rate_usd
