from evennia import DefaultScript


class AthanorScript(DefaultScript):
    """
    Base Athanor script all Athanor scripts should inherit from.

    It might do something new eventually.
    """


class AthanorParty(AthanorScript):
    """
    Base Athanor Script which handles a party of characters.

    This is meant to only accept AthanorPlayerCharacters as members.
    """

    def at_script_creation(self):
        super().at_script_creation()
        self.db.members = []
        self.db.leader = None
        self.db.name = "Party"
        self.db.description = "A party of characters."

    def make_leader(self, character, **kwargs):
        self.add_member(character, **kwargs)
        old_leader = self.db.leader
        self.db.leader = character
        self.on_leader_change(old_leader, character, **kwargs)

    def on_leader_change(self, old_leader, new_leader, **kwargs):
        pass

    def add_member(self, character, **kwargs):
        if character not in self.db.members:
            character.db.party = self
            self.db.members.append(character)
            self.on_join(character, **kwargs)

    def on_join(self, character, **kwargs):
        pass

    def remove_member(self, character, **kwargs):
        if character in self.db.members:
            character.db.party = None
            self.db.members.remove(character)
            self.on_leave(character, **kwargs)

    def on_leave(self, character, **kwargs):
        pass

    @property
    def characters(self):
        return [char for char in self.db.members if char]

    @property
    def online_characters(self):
        return [char for char in self.characters if char.db.is_online]
