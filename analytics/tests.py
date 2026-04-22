from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ingestion.models import ActivityLog
from users.models import CustomUser, Department

from .models import ToolCost


class ToolCostTests(TestCase):
    def test_value_per_action_math(self):
        tc = ToolCost.objects.create(
            tool_name='copilot',
            display_name='Copilot',
            monthly_cost_per_seat_usd=20,
            minutes_saved_per_action=6,  # 0.1 hr
            avg_hourly_rate_usd=100,
        )
        # 6 min * $100/hr = $10 per action
        self.assertAlmostEqual(tc.value_per_action_usd, 10.0, places=4)


class RoiDashboardViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.dept = Department.objects.create(name='Eng')
        self.user = CustomUser.objects.create(username='dev', department=self.dept)

        ToolCost.objects.create(
            tool_name='github_copilot',
            display_name='GitHub Copilot',
            monthly_cost_per_seat_usd=20,
            minutes_saved_per_action=3,
            avg_hourly_rate_usd=100,
        )

        # 10 recent copilot actions
        for _ in range(10):
            ActivityLog.objects.create(
                tool_name='github_copilot',
                user=self.user,
                user_email=self.user.email,
                action_type='completion',
                value_metric=1.0,
            )

    def test_staff_required(self):
        resp = self.client.get(reverse('analytics:roi_dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_renders_for_staff(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('analytics:roi_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'analytics/roi_dashboard.html')
        self.assertTrue(resp.context['has_costs_configured'])
        # Value = 3 min/60 * $100 * 10 actions = $50
        self.assertEqual(resp.context['total_value'], 50.0)
        # Cost = $20 * 1 seat
        self.assertEqual(resp.context['total_cost'], 20.0)
        self.assertEqual(resp.context['net_value'], 30.0)

    def test_dashboard_empty_state(self):
        ToolCost.objects.all().delete()
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('analytics:roi_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['has_costs_configured'])
