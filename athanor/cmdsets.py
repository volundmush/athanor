"""
The Athanor CmdSets are designed to load up their commands from modules specified in settings.py.

This makes managing commands much easier, as you can simply add a new module to the list and it will be loaded up.
"""

from evennia import default_cmds, CmdSet
import athanor


class PlayviewCmdSet(CmdSet):
    key = "PlayviewCmdset"

    def at_cmdset_creation(self):
        for cmd in athanor.CMD_MODULES_PLAYVIEW:
            self.add(cmd)


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "AthanorCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        for cmd in athanor.CMD_MODULES_CHARACTER:
            self.add(cmd)


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "AthanorAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        from evennia.commands.default.account import CmdQuit, CmdOOC

        self.remove(CmdQuit)
        self.remove(CmdOOC)

        for cmd in athanor.CMD_MODULES_ACCOUNT:
            self.add(cmd)


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "AthanorUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        for cmd in athanor.CMD_MODULES_UNLOGGEDIN:
            self.add(cmd)


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "AthanorSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        for cmd in athanor.CMD_MODULES_SESSION:
            self.add(cmd)
