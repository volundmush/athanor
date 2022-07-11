from django.db import models
from django.conf import settings
from evennia.typeclasses.models import TypedObject, SharedMemoryModel


class DGScriptDB(TypedObject):

    __settingsclasspath__ = settings.BASE_DGSCRIPT_TYPECLASS
    __defaultclasspath__ = "athanor.dgscripts.dgscripts.DefaultDGScript"
    __applabel__ = "dgscripts"

    db_color_name = models.CharField(max_length=150)
    db_attach_type = models.IntegerField(default=0)
    db_trigger_type = models.PositiveIntegerField(default=0)
    db_data_type = models.IntegerField(default=0)
    db_narg = models.SmallIntegerField(default=0)
    db_arglist = models.CharField(max_length=255)
    db_lines = models.JSONField(default=list)

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.id}): {self.db_key}>"


class DGInstanceDB(SharedMemoryModel):
    __applabel__ = "dgscripts"

    db_script = models.ForeignKey(DGScriptDB, related_name='instances', on_delete=models.PROTECT)
    db_holder = models.ForeignKey('objects.ObjectDB', related_name='dg_scripts', on_delete=models.CASCADE)
    db_state = models.PositiveSmallIntegerField(default=0)

