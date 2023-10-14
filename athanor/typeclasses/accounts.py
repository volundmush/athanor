from evennia.accounts.accounts import DefaultAccount
from evennia.utils.ansi import parse_ansi, ANSIString
from evennia.utils.evtable import EvTable


class AthanorAccount(DefaultAccount):
    def is_admin(self) -> bool:
        return self.locks.check_lockstring(self, "perm(Admin)")

    def table(self, *args, **kwargs) -> EvTable:
        """
        Generates/instantiates an Evtable styled for the user's preferences.
        """
        default_kwargs = {
            "width": 78,
            "corner_char": ANSIString("|M+|n"),
            "header_line_char": ANSIString("|M~|n"),
            "border_char": ANSIString("|M-|n"),
            "border_left_char": ANSIString("|M|||n"),
            "border_right_char": ANSIString("|M|||n"),
        }
        default_kwargs.update(kwargs)

        if self.get_option("screenreader"):
            default_kwargs["border"] = None

        args = [
            ANSIString(f"|w{arg}|n") if not isinstance(arg, ANSIString) else arg
            for arg in args
        ]
        return EvTable(*args, **default_kwargs)

    def get_option(self, option: str):
        pass
