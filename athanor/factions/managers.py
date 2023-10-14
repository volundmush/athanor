from django.db import models
from django.conf import settings
from evennia.typeclasses.managers import TypeclassManager, TypedObjectManager


class FactionDBManager(TypedObjectManager):
    system_name = "FACTION"


class FactionManager(FactionDBManager, TypeclassManager):
    pass


class RankManager(models.Manager):
    system_name = "FACTION"


class MemberManager(models.Manager):
    system_name = "FACTION"
