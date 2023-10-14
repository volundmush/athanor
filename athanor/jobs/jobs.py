from evennia.typeclasses.models import TypeclassBase

from .managers import BucketManager

from .models import BucketDB


class DefaultBucket(BucketDB, metaclass=TypeclassBase):
    system_name = "JOB"
    objects = BucketManager()
