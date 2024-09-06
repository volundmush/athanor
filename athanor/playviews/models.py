from django.db import models
from django.conf import settings
from django.core.validators import validate_comma_separated_integer_list
from evennia.typeclasses.models import TypedObject
from athanor.playviews.managers import PlayviewDBManager
from athanor.utils import utcnow


class PlayviewDB(TypedObject):
    objects = PlayviewDBManager()

    __settingsclasspath__ = settings.BASE_PLAYVIEW_TYPECLASS
    __defaultclasspath__ = "athanor.playviews.DefaultPlayview"
    __applabel__ = "athanor"

    id = models.OneToOneField(
        "objects.ObjectDB",
        primary_key=True,
        related_name="playview",
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        "accounts.AccountDB", on_delete=models.CASCADE, related_name="playviews"
    )
    db_puppet = models.OneToOneField(
        "objects.ObjectDB", related_name="puppeting_playview", on_delete=models.CASCADE
    )

    # the session id associated with this account, if any.
    # this is copied from ObjectDB.
    db_sessid = models.CharField(
        null=True,
        max_length=32,
        validators=[validate_comma_separated_integer_list],
        verbose_name="session id",
        help_text="csv list of session ids of connected Account, if any.",
    )

    db_last_active = models.DateTimeField(null=True, blank=True, default=utcnow)
