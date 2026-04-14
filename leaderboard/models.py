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
