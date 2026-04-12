from django.contrib import admin
from .models import ActivityLog, ConnectorConfig

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('tool_name', 'user_email', 'action_type', 'value_metric', 'processed')
    list_filter = ('processed', 'tool_name')
    search_fields = ('user_email', 'tool_name')

@admin.register(ConnectorConfig)
class ConnectorConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'webhook_slug', 'is_active', 'default_value')
    prepopulated_fields = {"webhook_slug": ("name",)}
    fieldsets = (
        ("General", {
            "fields": ("name", "webhook_slug", "is_active")
        }),
        ("JSON Payload Mapping", {
            "fields": ("email_json_path", "action_json_path", "value_json_path", "default_value"),
            "description": "Define the exact path keys sent in the third party's JSON webhook. (Note: deeply nested parsing using dots like 'actor.email' is supported by our parser)."
        }),
    )
