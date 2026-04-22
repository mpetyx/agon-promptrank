from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ingestion.models import ActivityLog
from scoring.models import ScoreLog
from users.models import CustomUser, Department

from .models import ActionFeedItem, Clash, Season, SeasonArchive
from .tasks import _archive_season, publish_feed_item


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
        self.assertIn('streak', resp.context)
        self.assertIn('quest_rows', resp.context)

    def test_command_center_block(self):
        resp = self.client.get(reverse('command_center'))
        self.assertEqual(resp.status_code, 302)

    def test_command_center_allow(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('command_center'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'leaderboard/command_center.html')

    def test_stats_api(self):
        resp = self.client.get(reverse('stats_webhooks'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('total' in resp.json())


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
            start_date=now - timedelta(days=1), end_date=now + timedelta(days=1),
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


class SeasonTests(TestCase):
    def setUp(self):
        self.d1 = Department.objects.create(name="Engineering")
        self.alice = CustomUser.objects.create(username="alice", department=self.d1)
        self.bob = CustomUser.objects.create(username="bob", department=self.d1)
        now = timezone.now()

        # A live season
        self.live = Season.objects.create(
            name="Spring 2026",
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=30),
        )
        # An ended (not yet archived) season
        self.ended = Season.objects.create(
            name="Winter 2026",
            start_date=now - timedelta(days=120),
            end_date=now - timedelta(days=40),
        )

        # Score 1 — inside live season
        alog = ActivityLog.objects.create(tool_name="x", user=self.alice, action_type="a", value_metric=10)
        ScoreLog.objects.create(user=self.alice, activity_log=alog, base_points=10, multiplier_applied=1, final_points=25)

        # Score 2 — inside ended season (bob wins the ended season)
        blog = ActivityLog.objects.create(tool_name="x", user=self.bob, action_type="a", value_metric=40)
        sl = ScoreLog.objects.create(user=self.bob, activity_log=blog, base_points=40, multiplier_applied=1, final_points=40)
        ScoreLog.objects.filter(id=sl.id).update(created_at=now - timedelta(days=60))

    def test_is_active_flag(self):
        self.assertTrue(self.live.is_active)
        self.assertFalse(self.ended.is_active)
        self.assertTrue(self.ended.has_ended)

    def test_season_leaderboard_filters_by_date(self):
        # Live season should only see alice's recent score
        lb = list(self.live.get_leaderboard())
        self.assertEqual(lb[0], self.alice)

    def test_archive_season_creates_snapshot_and_feed_item(self):
        _archive_season(self.ended)
        self.ended.refresh_from_db()
        self.assertTrue(self.ended.is_archived)
        self.assertTrue(SeasonArchive.objects.filter(season=self.ended, user=self.bob, rank=1).exists())
        self.assertTrue(ActionFeedItem.objects.filter(event_type='season', user=self.bob).exists())

    def test_hall_of_fame_view(self):
        _archive_season(self.ended)
        resp = self.client.get(reverse('hall_of_fame'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Winter 2026")

    def test_season_detail_view(self):
        _archive_season(self.ended)
        resp = self.client.get(reverse('season_detail', args=[self.ended.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "bob")


class ActionFeedTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="ticker")

    def test_publish_feed_item_creates_row(self):
        publish_feed_item(self.user.id, 'clash', 'Something cool happened', icon='🎉')
        self.assertTrue(ActionFeedItem.objects.filter(user=self.user, event_type='clash').exists())

    def test_feed_poll_endpoint_returns_partial(self):
        ActionFeedItem.objects.create(user=self.user, event_type='badge', message='x', icon='🏆')
        resp = self.client.get(reverse('feed_poll'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'leaderboard/partials/action_ticker.html')
        self.assertContains(resp, 'x')

    def test_feed_poll_empty_state(self):
        resp = self.client.get(reverse('feed_poll'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No activity yet')


class ArenaSeasonFilterTests(TestCase):
    def setUp(self):
        self.u = CustomUser.objects.create(username="solo")
        now = timezone.now()
        self.season = Season.objects.create(
            name="Live",
            start_date=now - timedelta(days=2),
            end_date=now + timedelta(days=5),
        )
        log = ActivityLog.objects.create(tool_name="x", user=self.u, action_type="a", value_metric=7)
        ScoreLog.objects.create(user=self.u, activity_log=log, base_points=7, multiplier_applied=1, final_points=7)

    def test_season_filter_mode(self):
        resp = self.client.get(reverse('arena') + '?filter=season')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['filter_mode'], 'season')
        self.assertEqual(resp.context['current_season'], self.season)

    def test_this_week_filter(self):
        resp = self.client.get(reverse('arena') + '?filter=this_week')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['filter_mode'], 'this_week')
