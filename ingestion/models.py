from django.db import models
from users.models import CustomUser

class ActivityLog(models.Model):
    tool_name = models.CharField(max_length=100, db_index=True)
    user_email = models.EmailField(db_index=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    action_type = models.CharField(max_length=100)
    value_metric = models.FloatField()
    raw_payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.tool_name} activity by {self.user_email} at {self.created_at} "

class ConnectorConfig(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Ex: ChatGPT Enterprise")
    webhook_slug = models.SlugField(unique=True, help_text="Creates a unique URL ending: /api/v1/ingest/<slug>/")
    
    # JSON Path Mapping Rules
    email_json_path = models.CharField(max_length=100, help_text="Dictionary key holding the user's email. Ex: 'actor.email' or 'email'")
    action_json_path = models.CharField(max_length=100, help_text="Dictionary key holding the log event. Ex: 'event_type'")
    value_json_path = models.CharField(max_length=100, blank=True, help_text="Optional. Key holding point metrics. Ex: 'complexity'")
    
    default_value = models.FloatField(default=1.0, help_text="Fallback points if value_json_path fails or is empty.")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
