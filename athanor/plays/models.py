from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject
from athanor.utils import utcnow


class PlayDB(TypedObject):
    id = models.OneToOneField('objects.ObjectDB', related_name='play', on_delete=models.PROTECT, primary_key=True)
    db_puppet = models.OneToOneField('objects.ObjectDB', related_name='puppeteer', on_delete=models.PROTECT)
    db_account = models.ForeignKey("accounts.AccountDB", on_delete=models.PROTECT, related_name="plays", null=False)
    db_sessid = models.JSONField(default=list)
    db_cmdset_storage = models.JSONField(default=list)
    db_last_good = models.DateTimeField(editable=True, default=utcnow)
    db_last_activity = models.DateTimeField(editable=True, default=utcnow)
    db_timeout_seconds = models.FloatField(default=0.0)

    __settingsclasspath__ = settings.BASE_PLAY_TYPECLASS
    __defaultclasspath__ = "athanor.plays.plays.DefaultPlay"
    __applabel__ = "game"

    class Meta:
        verbose_name = "Play"
        verbose_name_plural = "Plays"