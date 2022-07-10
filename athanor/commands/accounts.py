from .base import AccountCommand
from athanor.utils import partial_match


class CmdPlay(AccountCommand):
    """
    Enter play as one of your characters!

    Usage:
        play <character>
    """
    key = "play"
    help_category = "General"
    locks = "cmd:is_ooc()"

    def func(self):
        candidates = self.account.get_characters()

        if not self.args:
            self.msg("Usage: play <character>")
            return

        if not (found := partial_match(self.args, candidates, key=lambda x: x.key)):
            self.msg("That is not a valid character choice.")
            return