from django.db import models
from django.conf import settings

from evennia.typeclasses.models import TypedObject


class BoardCategoryDB(TypedObject):
    __settingsclasspath__ = settings.BASE_BOARD_CATEGORY_TYPECLASS
    __defaultclasspath__ = "athanor.db.boards.boards.DefaultBoardCategory"
    __applabel__ = "boards"

    db_color_name = models.CharField(max_length=255, blank=False, null=True)
    db_abbr = models.CharField(max_length=8, null=False, blank=True, unique=True)
    db_order = models.PositiveIntegerField(default=0, null=False)


class BoardDB(TypedObject):
    __settingsclasspath__ = settings.BASE_BOARD_TYPECLASS
    __defaultclasspath__ = "athanor.db.boards.boards.DefaultBoard"
    __applabel__ = "boards"

    db_category = models.ForeignKey(BoardCategoryDB, related_name='boards', on_delete=models.CASCADE)
    db_color_name = models.CharField(max_length=255, blank=False, null=True)
    db_order = models.PositiveIntegerField(default=0, null=False)
    ignoring = models.ManyToManyField('accounts.AccountDB', related_name='ignored_boards')


    class Meta:
        unique_together = (("db_category", "db_order"),)


class BoardTopic(TypedObject):
    __settingsclasspath__ = settings.BASE_BOARD_TOPIC_TYPECLASS
    __defaultclasspath__ = "athanor.db.boards.boards.DefaultBoardTopic"
    __applabel__ = "boards"

    db_board = models.ForeignKey(BoardDB, related_name='topics', on_delete=models.CASCADE)
    db_creator = models.ForeignKey("accounts.AccountDB", related_name="board_topics", on_delete=models.PROTECT)
    db_color_name = models.CharField(max_length=255, blank=False, null=True)
    db_order = models.PositiveIntegerField(default=0, null=False)
    db_date_modified = models.DateTimeField(null=False)
    db_date_latest = models.DateTimeField(null=False)

    class Meta:
        verbose_name = 'Topics'
        verbose_name_plural = 'Topics'
        unique_together = (('db_board', 'db_order'),)


class BoardPost(TypedObject):
    __settingsclasspath__ = settings.BASE_BOARD_POST_TYPECLASS
    __defaultclasspath__ = "athanor.db.boards.boards.DefaultBoardPost"
    __applabel__ = "boards"

    db_topic = models.ForeignKey(BoardTopic, related_name='posts', on_delete=models.CASCADE)
    db_author = models.ForeignKey('accounts.AccountDB', null=True, related_name='board_posts',
                                  on_delete=models.PROTECT)
    db_color_name = models.CharField(max_length=255, blank=False, null=True)
    db_date_modified = models.DateTimeField(null=False)
    db_order = models.PositiveIntegerField(null=False)
    db_body = models.TextField(null=False, blank=False)
    db_cbody = models.TextField(null=False, blank=False)

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        unique_together = (('db_topic', 'db_order'),)


class TopicRead(models.Model):
    account = models.ForeignKey('accounts.AccountDB', related_name='board_topic_read', on_delete=models.CASCADE)
    topic = models.ForeignKey(BoardTopic, related_name='readers', on_delete=models.CASCADE)
    date_read = models.DateTimeField(null=True)

    class Meta:
        unique_together = (('account', 'topic'),)
