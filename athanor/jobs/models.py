from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject
from .managers import BucketDBManager, JobManager, CommentManager


class BucketDB(TypedObject):
    objects = BucketDBManager()

    __settingsclasspath__ = settings.BASE_BUCKET_TYPECLASS
    __defaultclasspath__ = "athanor.jobs.jobs.DefaultBucket"
    __applabel__ = "jobs"

    db_key = models.CharField("key", max_length=255, unique=True)
    db_config = models.JSONField(null=False, default=dict)


class Job(models.Model):
    objects = JobManager()

    bucket = models.ForeignKey(BucketDB, on_delete=models.PROTECT, related_name="jobs")
    title = models.CharField(max_length=255, null=False, blank=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=True)
    date_modified = models.DateTimeField(auto_now=True, editable=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    date_due = models.DateTimeField(null=True, blank=True)
    date_player_activity = models.DateTimeField(null=True, blank=True)
    date_admin_activity = models.DateTimeField(null=True, blank=True)
    status = models.PositiveSmallIntegerField(default=0, null=False)
    config = models.JSONField(null=False, default=dict)
    characters = models.ManyToManyField("objects.ObjectDB", related_name="jobs")

    class Meta:
        index_together = (("bucket", "date_created"),)
        ordering = ["bucket", "-date_created"]


class Link(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="links")
    user = models.ForeignKey(
        "accounts.AccountDB", on_delete=models.PROTECT, related_name="job_links"
    )
    date_created = models.DateTimeField(auto_now_add=True, editable=True)
    status = models.PositiveSmallIntegerField(default=0, null=False)
    date_checked = models.DateTimeField(null=True, blank=True)


class Comment(models.Model):
    objects = CommentManager()

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="comments")
    date_created = models.DateTimeField(auto_now_add=True, editable=True)
    text = models.TextField(null=False, blank=False)
    type = models.PositiveSmallIntegerField(default=0, null=False)
    is_visible = models.BooleanField(default=True, null=False)
    data = models.JSONField(null=False, default=dict)

    class Meta:
        ordering = ["-date_created"]
