"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""
from django.conf import settings

from evennia import DefaultAccount


class AthanorAccount(DefaultAccount):

    def puppet_object(self, session, obj):
        # safety checks
        if not obj:
            raise RuntimeError("Object not found")
        if not session:
            raise RuntimeError("Session not found")
        if not obj.access(self, "puppet"):
            # no access
            session.msg(f"You don't have permission to puppet '{obj.key}'.")
            return
        if (found := self.plays.filter(id=obj).first()):
            # we don't care how many sessions are linked to the same play which already exists.
            session.create_or_join_play(obj)
        else:
            # it doesn't exist, which means we may not have permission to create another.
            if self.plays.all().count() >= settings.PLAYS_PER_ACCOUNT and not self.locks.check_lockstring(self, "perm(Builder)"):
                raise RuntimeError(f"You have reached the maximum {settings.PLAYS_PER_ACCOUNT} characters in play.")
            session.create_or_join_play(obj)

    def get_characters(self):
        return self.db._playable_characters