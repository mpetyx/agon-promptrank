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
