from django.db import models
from django.conf import settings
from django.core.validators import validate_comma_separated_integer_list
from evennia.typeclasses.models import TypedObject
from evennia.utils.utils import make_iter
from .managers import PlayviewDBManager
from .utils import utcnow


class AccountPlaytime(models.Model):
    id = models.OneToOneField(
        "accounts.AccountDB",
        primary_key=True,
        related_name="playtime",
        on_delete=models.CASCADE,
    )
    total_playtime = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CharacterPlaytime(models.Model):
    id = models.OneToOneField(
        "objects.ObjectDB",
        primary_key=True,
        related_name="+",
        on_delete=models.CASCADE,
    )
    total_playtime = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CharacterAccountPlaytime(models.Model):
    playtime = models.ForeignKey(
        CharacterPlaytime, on_delete=models.CASCADE, related_name="per_account"
    )
    account = models.ForeignKey(
        "accounts.AccountDB",
        on_delete=models.CASCADE,
        related_name="characters_playtime",
    )
    total_playtime = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("playtime", "account")


class AccountOwner(models.Model):
    id = models.OneToOneField(
        "objects.ObjectDB",
        primary_key=True,
        related_name="account_owner",
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        "accounts.AccountDB", related_name="owned_characters", on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.id)


class Host(models.Model):
    ip = models.GenericIPAddressField(unique=True)
    hostname = models.CharField(max_length=255, null=True)


class LoginRecord(models.Model):
    host = models.ForeignKey(Host, on_delete=models.PROTECT, related_name="records")
    account = models.ForeignKey(
        "accounts.AccountDB", on_delete=models.CASCADE, related_name="login_records"
    )
    is_success = models.BooleanField(default=False)
    reason = models.CharField(max_length=50, null=True, blank=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=True)


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

    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField(
        "cmdset",
        max_length=255,
        null=True,
        blank=True,
        help_text="optional python path to a cmdset class.",
    )

    # cmdset_storage property handling
    def __cmdset_storage_get(self):
        """getter"""
        storage = self.db_cmdset_storage
        return [path.strip() for path in storage.split(",")] if storage else []

    def __cmdset_storage_set(self, value):
        """setter"""
        self.db_cmdset_storage = ",".join(str(val).strip() for val in make_iter(value))
        self.save(update_fields=["db_cmdset_storage"])

    def __cmdset_storage_del(self):
        """deleter"""
        self.db_cmdset_storage = None
        self.save(update_fields=["db_cmdset_storage"])

    cmdset_storage = property(
        __cmdset_storage_get, __cmdset_storage_set, __cmdset_storage_del
    )
