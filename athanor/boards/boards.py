import re
from evennia.typeclasses.models import TypeclassBase

from .managers import BoardManager, CollectionManager
from .models import BoardDB, BoardCollectionDB, Post


class DefaultBoardCollection(BoardCollectionDB, metaclass=TypeclassBase):
    system_name = "BBS"
    objects = CollectionManager()

    def at_first_save(self):
        pass

    def serialize(self):
        return {"db_key": self.db_key, "db_abbreviation": self.db_abbreviation}


class DefaultBoard(BoardDB, metaclass=TypeclassBase):
    system_name = "BBS"
    objects = BoardManager()

    def at_first_save(self):
        pass

    def board_id(self):
        return f"{self.db_collection.db_abbreviation}{self.db_order}"

    def serialize(self):
        return {}
