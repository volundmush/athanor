from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject


class DGScriptDB(TypedObject):
    __settingsclasspath__ = settings.BASE_DGSCRIPT_TYPECLASS
    __defaultclasspath__ = "athanor.dgscripts.dgscripts.DefaultDGScript"
    __applabel__ = "dgscripts"

    db_color_name = models.CharField(max_length=150)
    db_attach_type = models.IntegerField(default=0)
    db_trigger_type = models.JSONField(null=True)
    db_data_type = models.IntegerField(default=0)
    db_narg = models.SmallIntegerField(default=0)
    db_arglist = models.CharField(max_length=255)
    db_lines = models.JSONField()