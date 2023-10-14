from django.conf import settings
from evennia.utils import class_from_module

from athanor.utils import Request
from athanor.commands import AthanorAccountCommand

from .models import Post


class _CmdBcBase(AthanorAccountCommand):
    locks = "cmd:perm(bbadmin) or perm(Admin)"
    help_category = "BBS"


class CmdBcCreate(_CmdBcBase):
    """
    Create a BBS Board Collection.

    Syntax:
        bccreate <abbreviation>=<name>

    Abbreviations must be 1-10 characters long and contain only letters.
    Use the string 'None' to create a board collection without an abbreviation.
    Abbreviations and names must be unique (case insensitive).
    """

    key = "bccreate"

    def func(self):
        if not (self.lhs and self.rhs):
            self.msg("Usage: bccreate <abbreviation>=<name>")
            return

        if self.lhs.lower() == "none":
            self.lhs = ""

        col = class_from_module(settings.BASE_BOARD_COLLECTION_TYPECLASS)

        req = Request(
            target=col.objects,
            user=self.caller,
            character=self.character,
            operation="create",
            kwargs={"name": self.rhs, "abbreviation": self.lhs},
        )
        req.execute()


class CmdBcRename(_CmdBcBase):
    """
    Rename a BBS Board Collection.

    Syntax:
        bcrename <abbreviation>=<name>
    """

    key = "bcrename"

    def func(self):
        if not (self.lhs and self.rhs):
            self.msg("Usage: bcrename <abbreviation>=<name>")
            return

        col = class_from_module(settings.BASE_BOARD_COLLECTION_TYPECLASS)

        req = Request(
            target=col.objects,
            user=self.caller,
            character=self.character,
            operation="rename",
            kwargs={"name": self.rhs, "collection_id": self.lhs},
        )
        req.execute()


class CmdBcAbbreviate(_CmdBcBase):
    """
    Rename a BBS Board Collection.

    Syntax:
        bcabbrev <abbreviation>=<new abbreviation>
    """

    key = "bcabbrev"

    def func(self):
        if not (self.lhs and self.rhs):
            self.msg("Usage: bcabbrev <abbreviation>=<new abbreviation>")
            return

        col = class_from_module(settings.BASE_BOARD_COLLECTION_TYPECLASS)

        req = Request(
            target=col.objects,
            user=self.caller,
            character=self.character,
            operation="rename",
            kwargs={"abbreviation": self.rhs, "collection_id": self.lhs},
        )
        req.execute()


class CmdBcLock(_CmdBcBase):
    key = "bclock"


class CmdBcDelete(_CmdBcBase):
    key = "bcdelete"


class _CmdBbBase(AthanorAccountCommand):
    help_category = "BBS"


class CmdBbCreate(_CmdBbBase):
    """
    Create a BBS Board.

    Syntax:
        bbcreate <collection abbreviation>[/<order>]=<name>
    """

    key = "bbcreate"

    def func(self):
        if not (self.lhs and self.rhs):
            self.msg("Usage: bcabbrev <abbreviation>[/<order>]=<name>")
            return

        b = class_from_module(settings.BASE_BOARD_TYPECLASS)

        if "/" in self.lhs:
            collection_id, order = self.lhs.split("/", 1)
        else:
            collection_id, order = self.lhs, None

        if collection_id.lower() == "none":
            collection_id = ""

        kwargs = {"name": self.rhs, "collection_id": collection_id}
        if order is not None:
            kwargs["order"] = order

        req = Request(
            target=b.objects,
            user=self.caller,
            character=self.character,
            operation="create",
            kwargs=kwargs,
        )
        req.execute()


class CmdBbRename(_CmdBbBase):
    key = "bbrename"

    def func(self):
        pass


class CmdBbPost(_CmdBbBase):
    """
    Post a message to a BBS Board.

    Syntax:
        bbpost <board id>/<subject>=<message>
    """

    key = "bbpost"

    def func(self):
        if not (self.lhs and self.rhs):
            self.msg("Usage: bbpost <board id>/<subject>=<message>")
            return

        if "/" not in self.lhs:
            self.msg("Usage: bbpost <board id>/<subject>=<message>")
            return

        board_id, subject = self.lhs.split("/", 1)

        req = Request(
            target=Post.objects,
            user=self.caller,
            character=self.character,
            operation="create",
            kwargs={"board_id": board_id, "subject": subject, "body": self.rhs},
        )
        req.execute()
