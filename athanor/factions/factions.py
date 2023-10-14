from evennia.typeclasses.models import TypeclassBase

from .managers import FactionManager
from .models import FactionDB


class DefaultFaction(FactionDB, metaclass=TypeclassBase):
    system_name = "FACTION"
    objects = FactionManager()
