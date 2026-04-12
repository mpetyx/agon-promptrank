from django.contrib.auth.models import AbstractUser
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    handicap_multiplier = models.FloatField(default=1.0, help_text="Multiplier to level the playing field across roles.")

    def __str__(self) -> str:
        return self.name

class CustomUser(AbstractUser):
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    slack_id = models.CharField(max_length=100, blank=True)
    github_handle = models.CharField(max_length=100, blank=True)
    is_anonymized = models.BooleanField(default=False, help_text="Opt-out for privacy.")

    def __str__(self) -> str:
        if self.is_anonymized:
            return f"User {self.pk} (Anonymous)"
        return self.email or self.username
