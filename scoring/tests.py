from django.test import TestCase
from users.models import CustomUser, Department
from ingestion.models import ActivityLog
from leaderboard.models import Badge, UserBadge
from .models import ScoreLog
from .tasks import process_activity_log, check_and_award_badges
from django.utils import timezone

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
            processed=False
        )
        msg = process_activity_log(log.id)
        self.assertTrue("Processed" in msg)
        
        score = ScoreLog.objects.get(activity_log=log)
        self.assertEqual(score.final_points, 10.0)  # 5.0 * 2.0 multiplier
        
    def test_process_activity_spam(self):
        # Create 11 logs directly to fake spam
        for i in range(11):
            ActivityLog.objects.create(
                user=self.user,
                tool_name="spam_tool",
                action_type="jump",
                value_metric=10.0,
                processed=True
            )
            
        new_log = ActivityLog.objects.create(
            user=self.user,
            tool_name="spam_tool",
            action_type="jump",
            value_metric=10.0,
            processed=False
        )
        process_activity_log(new_log.id)
        score = ScoreLog.objects.get(activity_log=new_log)
        # points = 10 * 0.1 (spam reduction) * 2.0 (dept multiplier) = 2.0
        self.assertEqual(score.final_points, 2.0)
        self.assertTrue("Anti-cheat" in score.reason)
        
    def test_badges_awarded(self):
        # Fake a score log that grants 10 points (threshold is 5)
        log = ActivityLog.objects.create(user=self.user, tool_name="x", action_type="y", value_metric=10)
        ScoreLog.objects.create(
            user=self.user,
            activity_log=log,
            base_points=10.0,
            multiplier_applied=1.0,
            final_points=10.0
        )
        check_and_award_badges(self.user.id)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge=self.badge).exists())
