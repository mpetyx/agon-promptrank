import os
import random

import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import timedelta

from analytics.models import ToolCost
from ingestion.models import ActivityLog
from leaderboard.models import ActionFeedItem, Badge, Clash, Season, SeasonArchive, UserBadge
from scoring.models import Quest, ScoreLog, UserQuestProgress, UserStreak
from users.models import CustomUser, Department


def run():
    print("Clearing old dummy data...")
    SeasonArchive.objects.all().delete()
    Season.objects.all().delete()
    ActionFeedItem.objects.all().delete()
    UserQuestProgress.objects.all().delete()
    Quest.objects.all().delete()
    UserStreak.objects.all().delete()
    ToolCost.objects.all().delete()
    ScoreLog.objects.all().delete()
    ActivityLog.objects.all().delete()
    UserBadge.objects.all().delete()
    Badge.objects.all().delete()
    Clash.objects.all().delete()
    CustomUser.objects.filter(is_superuser=False).delete()
    Department.objects.all().delete()

    # Departments
    eng = Department.objects.create(name="Engineering", handicap_multiplier=1.0)
    mktg = Department.objects.create(name="Marketing", handicap_multiplier=1.5)
    sales = Department.objects.create(name="Sales", handicap_multiplier=1.2)

    # Badges
    Badge.objects.create(name="First Blood", description="Earned your first points.", icon_svg="🩸", points_threshold=1)
    Badge.objects.create(name="Automation Initiate", description="100 points.", icon_svg="⚙️", points_threshold=100)
    Badge.objects.create(name="Cyborg Overlord", description="1000 points.", icon_svg="🤖", points_threshold=1000)

    # Seasons — one archived, one live, one upcoming
    now = timezone.now()
    past_season = Season.objects.create(
        name="Winter 2026",
        start_date=now - timedelta(days=120),
        end_date=now - timedelta(days=31),
        is_archived=False,  # will be archived after score logs are created
    )
    live_season = Season.objects.create(
        name="Spring 2026",
        start_date=now - timedelta(days=30),
        end_date=now + timedelta(days=60),
    )
    Season.objects.create(
        name="Summer 2026",
        start_date=now + timedelta(days=61),
        end_date=now + timedelta(days=150),
    )

    # Quests
    Quest.objects.create(
        name="Daily Copilot Warm-up",
        description="Accept 3 Copilot completions today.",
        tool_name="github_copilot",
        target_count=3,
        reward_points=3.0,
        scope='daily',
        icon='🤖',
    )
    Quest.objects.create(
        name="Cursor Sprinter",
        description="Fire 5 Cursor commands today.",
        tool_name="cursor",
        target_count=5,
        reward_points=5.0,
        scope='daily',
        icon='⚡',
    )
    Quest.objects.create(
        name="Tool Omnivore",
        description="Generate 20 actions this week across any AI tool.",
        target_count=20,
        reward_points=15.0,
        scope='weekly',
        icon='🌐',
    )

    # Tool costs (for ROI dashboard)
    ToolCost.objects.create(
        tool_name="github_copilot",
        display_name="GitHub Copilot Business",
        monthly_cost_per_seat_usd=19.0,
        minutes_saved_per_action=3.0,
        avg_hourly_rate_usd=90.0,
    )
    ToolCost.objects.create(
        tool_name="cursor",
        display_name="Cursor Pro",
        monthly_cost_per_seat_usd=20.0,
        minutes_saved_per_action=2.5,
        avg_hourly_rate_usd=90.0,
    )
    ToolCost.objects.create(
        tool_name="chatgpt",
        display_name="ChatGPT Enterprise",
        monthly_cost_per_seat_usd=60.0,
        minutes_saved_per_action=2.0,
        avg_hourly_rate_usd=85.0,
    )

    users_data = [
        ("alice", "alice@company.com", eng, "alice_git"),
        ("bob", "bob@company.com", mktg, None),
        ("charlie", "charlie@company.com", sales, "chuck_gh"),
        ("dave", "dave@company.com", eng, "dave_codes"),
        ("eve", "eve@company.com", eng, "eve_hacker"),
    ]
    users = []
    for uname, email, dept, gh in users_data:
        u = CustomUser.objects.create(username=uname, email=email, department=dept, github_handle=gh or "")
        users.append(u)

    # Clash across live season
    Clash.objects.create(
        name="Spring Sprint: Eng vs Marketing",
        department1=eng,
        department2=mktg,
        start_date=now - timedelta(days=7),
        end_date=now + timedelta(days=21),
    )

    # Generate scores
    tools = ['github_copilot', 'cursor', 'chatgpt']
    actions = ['completion_accepted', 'cmd_k', 'message_sent']

    from scoring.tasks import process_activity_log

    for _ in range(180):
        u = random.choice(users)
        tool = random.choice(tools)
        action = random.choice(actions)
        val = round(random.uniform(0.5, 5.0), 2)
        created_at = timezone.now() - timedelta(days=random.randint(0, 100))
        log = ActivityLog.objects.create(
            tool_name=tool,
            user_email=u.email,
            user=u,
            action_type=action,
            value_metric=val,
            raw_payload={"mock": "data"},
            created_at=created_at,
        )
        process_activity_log.delay(log.id)
        # Backdate the ScoreLog to match the ActivityLog so seasons/trends look realistic.
        ScoreLog.objects.filter(activity_log=log).update(created_at=created_at)

    # Archive the past season now that scores exist
    from leaderboard.tasks import archive_season as archive_season_task
    archive_season_task.delay(past_season.id)

    print(
        f"✅ Seed complete: {len(users)} users · 3 departments · 3 seasons · 3 quests · "
        f"3 tool costs · ~180 score logs. Past season archived. Fire up the Arena!"
    )


if __name__ == '__main__':
    run()
