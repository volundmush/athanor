import typing
from django.conf import settings
from evennia.objects.objects import DefaultCharacter, DefaultObject
import athanor
from athanor.utils import utcnow
from .mixin import AthanorObject


class AthanorCharacter(AthanorObject, DefaultCharacter):
    """
    Base class for Athanor characters.
    """

    lock_default_funcs = athanor.OBJECT_CHARACTER_DEFAULT_LOCKS
    _content_types = ("character",)
    lockstring = ""

    def basetype_setup(self):
        """
        Avoids calling super() in order to avoid setting unnecessary locks.
        """
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, persistent=True)

    def access_check_puppet(self, accessing_obj, **kwargs):
        """
        All characters can be puppeted by the Account they are assigned to,
        as a basic assumption.
        """
        if not (ao := getattr(self, "account_owner", None)):
            return False
        return ao.account == accessing_obj

    def at_post_puppet(self, **kwargs):
        """
        This explicitly does nothing, because the Playview system handles it.
        """

    def at_post_unpuppet(self, **kwargs):
        """
        This explicitly does nothing, because the Playview system handles it.
        """
