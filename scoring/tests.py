from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from ingestion.models import ActivityLog
from leaderboard.models import ActionFeedItem, Badge, UserBadge
from users.models import CustomUser, Department

from .models import Quest, ScoreLog, UserQuestProgress, UserStreak
from .tasks import (
    check_and_award_badges,
    check_point_milestones,
    process_activity_log,
    update_quest_progress,
    update_streak,
)


class ScoringTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Eng", handicap_multiplier=2.0)
        self.user = CustomUser.objects.create(username="player", email="player@test.com", department=self.dept)
        self.badge = Badge.objects.create(name="Bronze", points_threshold=5.0)

    def test_process_activity_normal(self):
        log = ActivityLog.objects.create(
            user=self.user,
            tool_name="tool",
            action_type="action",
            value_metric=5.0,
            processed=False,
        )
        msg = process_activity_log(log.id)
        self.assertTrue("Processed" in msg)

        score = ScoreLog.objects.get(activity_log=log)
        self.assertEqual(score.final_points, 10.0)

    def test_process_activity_spam(self):
        for i in range(11):
            ActivityLog.objects.create(
                user=self.user,
                tool_name="spam_tool",
                action_type="jump",
                value_metric=10.0,
                processed=True,
            )

        new_log = ActivityLog.objects.create(
            user=self.user,
            tool_name="spam_tool",
            action_type="jump",
            value_metric=10.0,
            processed=False,
        )
        process_activity_log(new_log.id)
        score = ScoreLog.objects.get(activity_log=new_log)
        self.assertEqual(score.final_points, 2.0)
        self.assertTrue("Anti-cheat" in score.reason)

    def test_badges_awarded(self):
        log = ActivityLog.objects.create(user=self.user, tool_name="x", action_type="y", value_metric=10)
        ScoreLog.objects.create(
            user=self.user,
            activity_log=log,
            base_points=10.0,
            multiplier_applied=1.0,
            final_points=10.0,
        )
        check_and_award_badges(self.user.id)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge=self.badge).exists())

    def test_badges_publish_feed_item(self):
        log = ActivityLog.objects.create(user=self.user, tool_name="x", action_type="y", value_metric=10)
        ScoreLog.objects.create(
            user=self.user,
            activity_log=log,
            base_points=10.0,
            multiplier_applied=1.0,
            final_points=10.0,
        )
        check_and_award_badges(self.user.id)
        self.assertTrue(ActionFeedItem.objects.filter(user=self.user, event_type='badge').exists())


class StreakTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username='runner', email='runner@test.com')

    def test_first_activity_starts_streak_at_one(self):
        update_streak(self.user.id)
        s = UserStreak.objects.get(user=self.user)
        self.assertEqual(s.current_streak, 1)
        self.assertEqual(s.longest_streak, 1)
        self.assertEqual(s.last_active_date, timezone.localdate())

    def test_same_day_update_is_idempotent(self):
        update_streak(self.user.id)
        update_streak(self.user.id)
        s = UserStreak.objects.get(user=self.user)
        self.assertEqual(s.current_streak, 1)

    def test_consecutive_day_increments(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        UserStreak.objects.create(user=self.user, current_streak=5, longest_streak=5, last_active_date=yesterday)
        update_streak(self.user.id)
        s = UserStreak.objects.get(user=self.user)
        self.assertEqual(s.current_streak, 6)
        self.assertEqual(s.longest_streak, 6)

    def test_gap_resets_streak(self):
        stale = timezone.localdate() - timedelta(days=3)
        UserStreak.objects.create(user=self.user, current_streak=10, longest_streak=10, last_active_date=stale)
        update_streak(self.user.id)
        s = UserStreak.objects.get(user=self.user)
        self.assertEqual(s.current_streak, 1)
        self.assertEqual(s.longest_streak, 10)  # longest preserved

    def test_milestone_emits_feed_item(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        UserStreak.objects.create(user=self.user, current_streak=2, longest_streak=2, last_active_date=yesterday)
        update_streak(self.user.id)
        self.assertTrue(ActionFeedItem.objects.filter(user=self.user, event_type='streak').exists())


class QuestTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username='quester', email='quester@test.com')
        self.quest = Quest.objects.create(
            name="Copilot Starter",
            description="Accept 2 Copilot completions today.",
            tool_name="github_copilot",
            target_count=2,
            reward_points=3.0,
            scope='daily',
        )

    def _make_log(self, tool='github_copilot'):
        return ActivityLog.objects.create(
            user=self.user, tool_name=tool, action_type='x', value_metric=1.0, processed=True,
        )

    def test_matching_tool_increments_progress(self):
        log = self._make_log()
        update_quest_progress(self.user.id, log.id)
        p = UserQuestProgress.objects.get(user=self.user, quest=self.quest)
        self.assertEqual(p.current_count, 1)
        self.assertIsNone(p.completed_at)

    def test_non_matching_tool_ignored(self):
        log = self._make_log(tool='unrelated')
        update_quest_progress(self.user.id, log.id)
        self.assertFalse(UserQuestProgress.objects.filter(user=self.user, quest=self.quest).exists())

    def test_completion_awards_reward_and_feed(self):
        log1 = self._make_log()
        update_quest_progress(self.user.id, log1.id)
        log2 = self._make_log()
        update_quest_progress(self.user.id, log2.id)

        p = UserQuestProgress.objects.get(user=self.user, quest=self.quest)
        self.assertIsNotNone(p.completed_at)

        # Synthetic reward ScoreLog exists for the quest
        reward_logs = ScoreLog.objects.filter(user=self.user, reason__icontains='Quest reward')
        self.assertEqual(reward_logs.count(), 1)
        self.assertEqual(reward_logs.first().final_points, 3.0)

        # Ticker entry posted
        self.assertTrue(ActionFeedItem.objects.filter(user=self.user, event_type='quest').exists())


class MilestoneTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username='climber', email='c@test.com')

    def test_crossing_milestone_emits_feed(self):
        # Seed the user to just below 50 pts
        log = ActivityLog.objects.create(user=self.user, tool_name='x', action_type='y', value_metric=49.0, processed=True)
        ScoreLog.objects.create(user=self.user, activity_log=log, base_points=49.0, multiplier_applied=1.0, final_points=49.0)

        # Now award 2 more and check milestone
        log2 = ActivityLog.objects.create(user=self.user, tool_name='x', action_type='y', value_metric=2.0, processed=True)
        ScoreLog.objects.create(user=self.user, activity_log=log2, base_points=2.0, multiplier_applied=1.0, final_points=2.0)
        check_point_milestones(self.user.id, 2.0)
        self.assertTrue(ActionFeedItem.objects.filter(user=self.user, event_type='milestone').exists())
