from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject
from .managers import FactionDBManager, RankManager, MemberManager


class FactionDB(TypedObject):
    objects = FactionDBManager()

    __settingsclasspath__ = settings.BASE_FACTION_TYPECLASS
    __defaultclasspath__ = "athanor.factions.factions.DefaultFaction"
    __applabel__ = "factions"

    db_key = models.CharField("key", max_length=255, unique=True)
    db_abbreviation = models.CharField(
        max_length=30, unique=True, null=False, blank=True
    )
    db_tier = models.IntegerField(default=1, null=False)
    db_config = models.JSONField(null=False, default=dict)

    class Meta:
        ordering = ["-db_tier", "db_key"]


class Rank(models.Model):
    objects = RankManager()

    faction = models.ForeignKey(
        FactionDB, on_delete=models.CASCADE, related_name="ranks"
    )
    name = models.CharField(max_length=255, null=False, blank=False)
    number = models.IntegerField(null=False)
    config = models.JSONField(null=False, default=dict)

    class Meta:
        ordering = ["faction", "number"]
        unique_together = (("faction", "name"), ("faction", "number"))


class Member(models.Model):
    objects = MemberManager()

    character = models.ForeignKey(
        "objects.ObjectDB", related_name="fact_ranks", on_delete=models.CASCADE
    )
    faction = models.ForeignKey(
        FactionDB, related_name="members", on_delete=models.CASCADE
    )
    rank = models.ForeignKey(Rank, related_name="holders", on_delete=models.PROTECT)
    data = models.JSONField(null=False, default=dict)

    class Meta:
        unique_together = (("character", "faction"),)
