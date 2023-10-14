from django.db import models
from django.conf import settings
from evennia.typeclasses.managers import TypeclassManager, TypedObjectManager


class BucketDBManager(TypedObjectManager):
    system_name = "JOB"


class BucketManager(BucketDBManager, TypeclassManager):
    pass


class JobManager(models.Manager):
    system_name = "JOB"


class CommentManager(models.Manager):
    system_name = "JOB"
