from evennia.typeclasses.managers import TypeclassManager, TypedObjectManager


class PlayviewDBManager(TypedObjectManager):
    system_name = "PLAYVIEW"


class PlayviewManager(PlayviewDBManager, TypeclassManager):
    pass
