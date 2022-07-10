from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject


class PlayDB(TypedObject):
    id = models.OneToOneField('objects.ObjectDB', related_name='play', on_delete=models.CASCADE, primary_key=True)
    db_puppet = models.OneToOneField('objects.ObjectDB', related_name='puppeteer', on_delete=models.SET_NULL, null=False)
    db_account = models.ForeignKey("accounts.AccountDB", on_delete=models.CASCADE, related_name="plays", null=False)
    db_sessid = models.JSONField(defauilt=list)
    db_cmdset_storage = models.JSONField(default=list)
    db_last_activity = models.DateTimeField(editable=True, auto_now_add=True)

    __settingsclasspath__ = settings.BASE_PLAY_TYPECLASS
    __defaultclasspath__ = "athanor.plays.plays.DefaultPlay"
    __applabel__ = "game"

    class Meta:
        verbose_name = "Play"
        verbose_name_plural = "Plays"