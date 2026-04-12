from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import ActivityLog, ConnectorConfig
from users.models import CustomUser

class IngestionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create(username="bot", email="bot@test.com")
        self.config = ConnectorConfig.objects.create(
            name="Test",
            webhook_slug="test-slug",
            email_json_path="email",
            action_json_path="event",
            value_json_path="points",
            default_value=2.0
        )
        
    def test_vanilla_webhook(self):
        url = reverse('api_ingest')
        data = {
            "tool_name": "generic",
            "user_email": "bot@test.com",
            "action_type": "commit",
            "value_metric": 5.0
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ActivityLog.objects.filter(user_email="bot@test.com").exists())
        
    def test_dynamic_webhook(self):
        url = reverse('api_ingest_dynamic', kwargs={'slug': 'test-slug'})
        data = {
            "email": "bot@test.com",
            "event": "run",
            "points": 10.0
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        log = ActivityLog.objects.get(tool_name="test-slug")
        self.assertEqual(log.value_metric, 10.0)
        
    def test_dynamic_webhook_fallback(self):
        url = reverse('api_ingest_dynamic', kwargs={'slug': 'test-slug'})
        data = {
            "email": "bot@test.com",
            "event": "run"
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        log = ActivityLog.objects.get(tool_name="test-slug")
        self.assertEqual(log.value_metric, 2.0)
