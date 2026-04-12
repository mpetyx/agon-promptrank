import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser, Department
from leaderboard.models import Badge, UserBadge
from ingestion.models import ActivityLog
from scoring.models import ScoreLog

def run():
    print("Clearing old dummy data...")
    ScoreLog.objects.all().delete()
    ActivityLog.objects.all().delete()
    UserBadge.objects.all().delete()
    Badge.objects.all().delete()
    CustomUser.objects.filter(is_superuser=False).delete()
    Department.objects.all().delete()
    
    # Create Departments
    eng = Department.objects.create(name="Engineering", handicap_multiplier=1.0)
    mktg = Department.objects.create(name="Marketing", handicap_multiplier=1.5)
    sales = Department.objects.create(name="Sales", handicap_multiplier=1.2)
    
    # Create Badges
    b1 = Badge.objects.create(name="First Blood", description="Earned your first points.", icon_svg="🩸", points_threshold=1)
    b2 = Badge.objects.create(name="Automation Initiate", description="100 points.", icon_svg="⚙️", points_threshold=100)
    b3 = Badge.objects.create(name="Cyborg Overlord", description="1000 points.", icon_svg="🤖", points_threshold=1000)

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
        
    # Generate scores
    tools = ['github_copilot', 'cursor', 'chatgpt']
    actions = ['completion_accepted', 'cmd_k', 'message_sent']
    
    for _ in range(150):
        u = random.choice(users)
        tool = random.choice(tools)
        action = random.choice(actions)
        val = round(random.uniform(0.5, 5.0), 2)
        
        # We can bypass Celery entirely and directly create ScoreLogs for speed,
        # but calling process_activity_log indirectly through model triggers tests the pipeline!
        log = ActivityLog.objects.create(
            tool_name=tool,
            user_email=u.email,
            user=u,
            action_type=action,
            value_metric=val,
            raw_payload={"mock": "data"},
            created_at=timezone.now() - timezone.timedelta(days=random.randint(0, 10))
        )
        # Note: Since CELERY_TASK_ALWAYS_EAGER=True, process_activity_log won't be inherently triggered by models unless the API was hit. Let's trigger it directly.
        from scoring.tasks import process_activity_log
        process_activity_log.delay(log.id)
        
    print(f"✅ Generated {len(users)} users, 3 departments, and 150 score logs!")

if __name__ == '__main__':
    run()
