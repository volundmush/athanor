from django.db import models


class Theme(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)


class Member(models.Model):
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="members")
    character = models.ForeignKey(
        "objects.ObjectDB", related_name="theme_members", on_delete=models.CASCADE
    )
    type = models.CharField(max_length=10, null=True, blank=False)
    data = models.JSONField(null=False, default=dict)

    class Meta:
        unique_together = (("theme", "character"),)
