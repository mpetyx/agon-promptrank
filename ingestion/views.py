from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ActivityLog
from users.models import CustomUser

class IngestionWebhookView(APIView):
    """
    Universal DRF webhook endpoint for ingestion.
    Expected schema:
    {
        "tool_name": "str",
        "user_email": "str",
        "action_type": "str",
        "value_metric": float
    }
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Validate minimal required fields
        required_fields = ['tool_name', 'user_email', 'action_type', 'value_metric']
        if not all(field in data for field in required_fields):
            return Response(
                {"error": "Missing required fields.", "required": required_fields},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        tool_name = data['tool_name']
        user_email = data['user_email']
        action_type = data['action_type']
        
        try:
            value_metric = float(data['value_metric'])
        except (ValueError, TypeError):
            return Response({"error": "value_metric must be a float."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Try to associate with a CustomUser if one exists matching the email
        user = CustomUser.objects.filter(email=user_email).first()
        
        log = ActivityLog.objects.create(
            tool_name=tool_name,
            user_email=user_email,
            user=user,
            action_type=action_type,
            value_metric=value_metric,
            raw_payload=data,
            processed=False
        )
        
        # Trigger Celery task asynchronously using scoring App
        from scoring.tasks import process_activity_log
        process_activity_log.delay(log.id)
        
        return Response({"status": "received", "activity_id": log.id}, status=status.HTTP_201_CREATED)

from django.shortcuts import get_object_or_404
from .models import ConnectorConfig

def _get_nested_value(data: dict, key_path: str, default=None):
    if not key_path:
        return default
    keys = key_path.split('.')
    val = data
    try:
        for k in keys:
            val = val[k]
        return val
    except (KeyError, TypeError):
        return default

class DynamicIngestionWebhookView(APIView):
    """
    Dynamic DRF webhook endpoint resolving fields via ConnectorConfig mapping.
    """
    def post(self, request, slug, *args, **kwargs):
        config = get_object_or_404(ConnectorConfig, webhook_slug=slug, is_active=True)
        data = request.data
        
        user_email = _get_nested_value(data, config.email_json_path)
        action_type = _get_nested_value(data, config.action_json_path)
        
        if config.value_json_path:
            raw_value = _get_nested_value(data, config.value_json_path)
            try:
                value_metric = float(raw_value)
            except (ValueError, TypeError):
                value_metric = config.default_value
        else:
            value_metric = config.default_value
            
        if not user_email or not action_type:
            return Response(
                {"error": "Failed to map required payload fields using configuration rules."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user = CustomUser.objects.filter(email=user_email).first()
        
        log = ActivityLog.objects.create(
            tool_name=config.webhook_slug,
            user_email=user_email,
            user=user,
            action_type=action_type,
            value_metric=value_metric,
            raw_payload=data,
            processed=False
        )
        
        from scoring.tasks import process_activity_log
        process_activity_log.delay(log.id)
        
        return Response({"status": "mapped and received", "activity_id": log.id}, status=status.HTTP_201_CREATED)
