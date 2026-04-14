from django.test import TestCase
from django.urls import reverse
from users.models import CustomUser

class LeaderboardViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser("adminuser", "admin@test.com", "pass")
        self.user = CustomUser.objects.create(username="regular")
        
    def test_arena_view(self):
        resp = self.client.get(reverse('arena'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'leaderboard/arena.html')
        
    def test_htmx_arena_view(self):
        resp = self.client.get(reverse('arena'), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'leaderboard/partials/arena_table.html')

    def test_trophy_room_view(self):
        resp = self.client.get(reverse('trophy_room', kwargs={'username': "regular"}))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'leaderboard/trophy_room.html')
        
    def test_command_center_block(self):
        resp = self.client.get(reverse('command_center'))
        self.assertEqual(resp.status_code, 302)  # Staff required redirect
        
    def test_command_center_allow(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('command_center'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'leaderboard/command_center.html')
        
    def test_stats_api(self):
        resp = self.client.get(reverse('stats_webhooks'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('total' in resp.json())

from users.models import Department
from .models import Clash
from django.utils import timezone
from datetime import timedelta
from scoring.models import ScoreLog
from ingestion.models import ActivityLog

class GamificationFeaturesTests(TestCase):
    def setUp(self):
        self.d1 = Department.objects.create(name="Engineering")
        self.d2 = Department.objects.create(name="Marketing")
        self.user1 = CustomUser.objects.create(username="eng1", department=self.d1)
        self.user2 = CustomUser.objects.create(username="eng2", department=self.d1)
        self.user3 = CustomUser.objects.create(username="mkt1", department=self.d2)

        now = timezone.now()
        self.clash = Clash.objects.create(
            name="Battle", department1=self.d1, department2=self.d2,
            start_date=now - timedelta(days=1), end_date=now + timedelta(days=1)
        )
        
        act1 = ActivityLog.objects.create(tool_name="copilot", user=self.user1, action_type="test", value_metric=10)
        act2 = ActivityLog.objects.create(tool_name="chatgpt", user=self.user2, action_type="test", value_metric=20)
        act3 = ActivityLog.objects.create(tool_name="midjourney", user=self.user3, action_type="test", value_metric=15)
        
        ScoreLog.objects.create(user=self.user1, activity_log=act1, base_points=10, multiplier_applied=1, final_points=10)
        ScoreLog.objects.create(user=self.user2, activity_log=act2, base_points=20, multiplier_applied=1, final_points=20)
        ScoreLog.objects.create(user=self.user3, activity_log=act3, base_points=15, multiplier_applied=1, final_points=15)

    def test_clash_scoring(self):
        self.assertTrue(self.clash.is_active)
        self.assertEqual(self.clash.dept1_score, 30.0)
        self.assertEqual(self.clash.dept2_score, 15.0)

    def test_rival_logic(self):
        resp = self.client.get(reverse('trophy_room', kwargs={'username': "eng1"}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['rival'], self.user2)

