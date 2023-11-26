from django.conf import settings
from .base import AthanorAccountCommand


class CmdOOC(AthanorAccountCommand):
    """
    Disconnect this session from the current character.
    Requires account menus to be enabled.

    Usage:
      ooc
    """

    key = "ooc"
    locks = "cmd:pperm(Player)"
    aliases = "unpuppet"
    help_category = "General"

    def func(self):
        """Implement function"""

        account = self.account
        session = self.session
        playview = session.playview

        if not playview:
            string = "You are already OOC."
            self.msg(string)
            return

        if settings.AUTO_PUPPET_ON_LOGIN:
            self.msg("This game has no account menu. Use QUIT instead.")
            return

        if playview.sessions.count() == 1:
            self.msg("No other connections are using this character. Use QUIT instead.")
            return

        playview.do_remove_session(session, logout_type="ooc")


class CmdQuit(AthanorAccountCommand):
    """
    QUIT the game.
    NOTE: case-sensitive!

    Usage:
      QUIT

    If you are currently controlling a character, this will logout
    the character for all linked connections. If account menus are
    enabled, it will return you to the account menu. Otherwise,
    it will disconnect you from the game.
    """

    key = "quit"
    switch_options = ("all",)
    locks = "cmd:all()"

    def func(self):
        if not self.raw_string.startswith("QUIT"):
            self.msg("You must use the QUIT command in all caps.")
            return

        account = self.account
        session = self.session
        playview = session.playview

        if not playview:
            nsess = account.sessions.count() - 1
            if nsess > 0:
                session.msg(
                    f"|RQuitting|n. {nsess} session(s) are still connected.",
                )
            else:
                session.msg("|RQuitting|n. Hope to see you again, soon.")
            account.disconnect_session_from_account(session, "quit")
            return
        else:
            playview.do_quit()
