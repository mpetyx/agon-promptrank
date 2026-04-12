from django.db import models
from users.models import CustomUser

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
