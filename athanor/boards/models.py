from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject
from athanor.boards.managers import BoardDBManager, CollectionDBManager


class BoardCollectionDB(TypedObject):
    objects = CollectionDBManager()

    __settingsclasspath__ = settings.BASE_BOARD_COLLECTION_TYPECLASS
    __defaultclasspath__ = "athanor.boards.boards.DefaultBoardCollection"
    __applabel__ = "boards"

    db_key = models.CharField("key", max_length=255, unique=True)
    db_abbreviation = models.CharField(
        max_length=30, unique=True, null=False, blank=True
    )
    db_config = models.JSONField(null=False, default=dict)


class BoardDB(TypedObject):
    objects = BoardDBManager()

    # defaults
    __settingsclasspath__ = settings.BASE_BOARD_TYPECLASS
    __defaultclasspath__ = "athanor.boards.boards.DefaultBoard"
    __applabel__ = "boards"

    db_collection = models.ForeignKey(
        BoardCollectionDB, on_delete=models.PROTECT, related_name="boards"
    )
    db_order = models.IntegerField(default=1, null=False)

    db_config = models.JSONField(null=False, default=dict)
    db_next_post_number = models.IntegerField(default=1, null=False)
    db_last_activity = models.DateTimeField(auto_now=True, editable=True)

    class Meta:
        unique_together = (("db_collection", "db_key"), ("db_collection", "db_order"))
        ordering = ["db_collection", "db_order"]


class Post(models.Model):
    board = models.ForeignKey(BoardDB, on_delete=models.CASCADE, related_name="posts")
    user = models.ForeignKey("accounts.AccountDB", on_delete=models.PROTECT)
    character = models.ForeignKey(
        "objects.ObjectDB", null=True, on_delete=models.PROTECT
    )
    disguise = models.CharField(max_length=255, null=True, blank=True)
    number = models.IntegerField(null=False)
    reply_number = models.IntegerField(null=False, default=0)

    subject = models.CharField(max_length=255, null=False)

    date_created = models.DateTimeField(auto_now_add=True, editable=True)
    date_modified = models.DateTimeField(auto_now=True, editable=True)

    body = models.TextField(null=False)

    read = models.ManyToManyField("accounts.AccountDB", related_name="read_posts")

    class Meta:
        unique_together = (("board", "number", "reply_number"),)
        ordering = ["board", "number", "reply_number"]
