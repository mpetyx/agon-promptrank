from django.db import models
from users.models import CustomUser, Department
from django.utils import timezone
from django.db.models import Sum

class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon_svg = models.TextField(blank=True, help_text="Tailwind/Heroicon SVG")
    points_threshold = models.FloatField(default=0.0)

    def __str__(self) -> str:
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self) -> str:
        return f"{self.badge.name} awarded to {self.user}"

class Clash(models.Model):
    name = models.CharField(max_length=150)
    department1 = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='clashes_as_dept1')
    department2 = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='clashes_as_dept2')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    def _get_dept_score(self, dept):
        from scoring.models import ScoreLog
        score = ScoreLog.objects.filter(
            user__department=dept,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).aggregate(Sum('final_points'))['final_points__sum']
        return round(score, 1) if score else 0.0

    @property
    def dept1_score(self):
        return self._get_dept_score(self.department1)

    @property
    def dept2_score(self):
        return self._get_dept_score(self.department2)

    def __str__(self):
        return f"{self.name} ({self.department1} vs {self.department2})"


class Season(models.Model):
    """Time-boxed leaderboard cycles. Prevents stagnation."""
    name = models.CharField(max_length=100, unique=True, help_text="Ex: 'Spring 2026' or 'Q2 Showdown'")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_archived = models.BooleanField(default=False, help_text="True once results are frozen into the Hall of Fame.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date and not self.is_archived

    @property
    def is_upcoming(self):
        return self.start_date > timezone.now()

    @property
    def has_ended(self):
        return self.end_date < timezone.now()

    def get_leaderboard(self, limit=None):
        from scoring.models import ScoreLog
        qs = CustomUser.objects.annotate(
            season_score=Sum(
                'score_logs__final_points',
                filter=models.Q(
                    score_logs__created_at__gte=self.start_date,
                    score_logs__created_at__lte=self.end_date,
                ),
            )
        ).exclude(season_score__isnull=True).order_by('-season_score')
        return qs[:limit] if limit else qs

    def __str__(self):
        return self.name


class SeasonArchive(models.Model):
    """Frozen snapshot of a user's rank within a completed season."""
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='archives')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='season_archives')
    rank = models.PositiveIntegerField()
    final_score = models.FloatField()
    department_name = models.CharField(max_length=100, blank=True, help_text="Snapshot of dept name at archive time.")
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('season', 'user')
        ordering = ['season', 'rank']

    def __str__(self):
        return f"#{self.rank} {self.user.username} — {self.season.name} ({self.final_score:.1f}pts)"


class ActionFeedItem(models.Model):
    """Ticker entries — badge earns, milestones, quest completions, level-ups."""
    EVENT_TYPES = [
        ('badge', 'Badge'),
        ('quest', 'Quest'),
        ('streak', 'Streak'),
        ('milestone', 'Milestone'),
        ('clash', 'Clash'),
        ('season', 'Season'),
        ('rival', 'Rival'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='feed_items')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
    message = models.CharField(max_length=255)
    icon = models.CharField(max_length=10, blank=True, default='⚡')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.event_type}] {self.message}"
