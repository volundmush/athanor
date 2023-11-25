import math
import datetime

from django.conf import settings
from evennia.accounts.accounts import DefaultAccount, CharactersHandler
from evennia.utils import lazy_property
from evennia.utils.ansi import ANSIString
from evennia.utils.evtable import EvTable

from rich.table import Table
from rich.box import ASCII2

import athanor
from athanor.utils import utcnow
from .mixin import AthanorLowBase, AthanorHandler


class AthanorCharactersHandler(CharactersHandler):
    def _ensure_playable_characters(self):
        # Overriden to do nothing. This method is rendered unnecessary thanks to Django.
        return

    def _clean(self):
        # Overriden to do nothing. This method is rendered unnecessary thanks to Django.
        return

    def add(self, character):
        if not (owner := getattr(character, "account_owner", None)):
            from athanor.models import AccountOwner

            AccountOwner.objects.create(id=character, account=self.owner)
        else:
            owner.account = self.account
            owner.save(update_fields=["account"])
        self.owner.at_post_add_character(character)

    def remove(self, character):
        if owner := getattr(character, "account_owner", None):
            owner.delete()
        self.owner.at_post_remove_character(character)

    def all(self):
        return [c.id for c in self.owner.owned_characters.all()]

    def count(self):
        return self.owner.owned_characters.count()


class AthanorAccount(AthanorHandler, AthanorLowBase, DefaultAccount):
    lock_access_funcs = athanor.ACCOUNT_ACCESS_FUNCTIONS
    _content_types = ("account",)

    @lazy_property
    def characters(self):
        return AthanorCharactersHandler(self)

    def uses_screenreader(self, session=None):
        return super().uses_screenreader(session=session) or self.options.get(
            "screenreader"
        )

    def at_post_login(self, session=None, **kwargs):
        athanor.EVENTS["account_at_post_login"].send(
            sender=self, session=session, **kwargs
        )
        super().at_post_login(session=session, **kwargs)

    def at_failed_login(self, session, **kwargs):
        athanor.EVENTS["account_at_failed_login"].send(
            sender=self, session=session, **kwargs
        )
        super().at_failed_login(session=session, **kwargs)

    def client_width(self):
        return self.options.get("client_width")

    def styled_table(self, *args, **kwargs):
        """
        Create an EvTable styled by on user preferences.

        Args:
            *args (str): Column headers. If not colored explicitly, these will get colors
                from user options.
        Keyword Args:
            any (str, int or dict): EvTable options, including, optionally a `table` dict
                detailing the contents of the table.
        Returns:
            table (EvTable): An initialized evtable entity, either complete (if using `table` kwarg)
                or incomplete and ready for use with `.add_row` or `.add_collumn`.

        """
        border_color = self.options.get("border_color")
        column_color = self.options.get("column_names_color")

        colornames = ["|%s%s|n" % (column_color, col) for col in args]

        h_line_char = kwargs.pop("header_line_char", "~")
        header_line_char = ANSIString(f"|{border_color}{h_line_char}|n")
        c_char = kwargs.pop("corner_char", "+")
        corner_char = ANSIString(f"|{border_color}{c_char}|n")

        b_left_char = kwargs.pop("border_left_char", "||")
        border_left_char = ANSIString(f"|{border_color}{b_left_char}|n")

        b_right_char = kwargs.pop("border_right_char", "||")
        border_right_char = ANSIString(f"|{border_color}{b_right_char}|n")

        b_bottom_char = kwargs.pop("border_bottom_char", "-")
        border_bottom_char = ANSIString(f"|{border_color}{b_bottom_char}|n")

        b_top_char = kwargs.pop("border_top_char", "-")
        border_top_char = ANSIString(f"|{border_color}{b_top_char}|n")

        table = EvTable(
            *colornames,
            header_line_char=header_line_char,
            corner_char=corner_char,
            border_left_char=border_left_char,
            border_right_char=border_right_char,
            border_top_char=border_top_char,
            border_bottom_char=border_bottom_char,
            width=self.client_width(),
            **kwargs,
        )
        return table

    def rich_table(self, *args, **kwargs) -> Table:
        real_kwargs = {
            "box": ASCII2,
            "border_style": self.options.get("rich_border_style"),
            "header_style": self.options.get("rich_header_style"),
            "title_style": self.options.get("rich_header_style"),
            "expand": True,
        }
        real_kwargs.update(kwargs)
        if self.uses_screenreader():
            real_kwargs["box"] = None
        return Table(*args, **real_kwargs)

    def _render_decoration(
        self,
        header_text=None,
        fill_character=None,
        edge_character=None,
        mode="header",
        color_header=True,
        width=None,
    ):
        """
        Helper for formatting a string into a pretty display, for a header, separator or footer.

        Keyword Args:
            header_text (str): Text to include in header.
            fill_character (str): This single character will be used to fill the width of the
                display.
            edge_character (str): This character caps the edges of the display.
            mode(str): One of 'header', 'separator' or 'footer'.
            color_header (bool): If the header should be colorized based on user options.
            width (int): If not given, the client's width will be used if available.

        Returns:
            string (str): The decorated and formatted text.

        """

        colors = dict()
        colors["border"] = self.options.get("border_color")
        colors["headertext"] = self.options.get("%s_text_color" % mode)
        colors["headerstar"] = self.options.get("%s_star_color" % mode)

        width = width or settings.CLIENT_DEFAULT_WIDTH
        if edge_character:
            width -= 2

        if header_text:
            if color_header:
                header_text = ANSIString(header_text).clean()
                header_text = ANSIString(
                    "|n|%s%s|n" % (colors["headertext"], header_text)
                )
            if mode == "header":
                begin_center = ANSIString(
                    "|n|%s<|%s* |n" % (colors["border"], colors["headerstar"])
                )
                end_center = ANSIString(
                    "|n |%s*|%s>|n" % (colors["headerstar"], colors["border"])
                )
                center_string = ANSIString(begin_center + header_text + end_center)
            else:
                center_string = ANSIString(
                    "|n |%s%s |n" % (colors["headertext"], header_text)
                )
        else:
            center_string = ""

        fill_character = self.options.get("%s_fill" % mode)

        remain_fill = width - len(center_string)
        if remain_fill % 2 == 0:
            right_width = remain_fill / 2
            left_width = remain_fill / 2
        else:
            right_width = math.floor(remain_fill / 2)
            left_width = math.ceil(remain_fill / 2)

        right_fill = ANSIString(
            "|n|%s%s|n" % (colors["border"], fill_character * int(right_width))
        )
        left_fill = ANSIString(
            "|n|%s%s|n" % (colors["border"], fill_character * int(left_width))
        )

        if edge_character:
            edge_fill = ANSIString("|n|%s%s|n" % (colors["border"], edge_character))
            main_string = ANSIString(center_string)
            final_send = (
                ANSIString(edge_fill)
                + left_fill
                + main_string
                + right_fill
                + ANSIString(edge_fill)
            )
        else:
            final_send = left_fill + ANSIString(center_string) + right_fill
        return final_send

    def styled_header(self, *args, **kwargs):
        """
        Create a pretty header.
        """

        if "mode" not in kwargs:
            kwargs["mode"] = "header"
        return self._render_decoration(*args, **kwargs)

    def styled_separator(self, *args, **kwargs):
        """
        Create a separator.

        """
        if "mode" not in kwargs:
            kwargs["mode"] = "separator"
        return self._render_decoration(*args, **kwargs)

    def styled_footer(self, *args, **kwargs):
        """
        Create a pretty footer.

        """
        if "mode" not in kwargs:
            kwargs["mode"] = "footer"
        return self._render_decoration(*args, **kwargs)

    def datetime_format(
        self, dt: datetime.datetime = None, template: str = "%Y-%m-%d %H:%M:%S"
    ):
        if not dt:
            dt = datetime.datetime.now()
        tz = self.options.get("timezone")
        dt = dt.astimezone(tz)
        return dt.strftime(template)

    @property
    def playtime(self):
        from athanor.models import AccountPlaytime

        return AccountPlaytime.objects.get_or_create(id=self)[0]

    def at_post_login(self, session=None, **kwargs):
        """
        Modified to track login time.
        """
        p = self.playtime
        p.last_login = utcnow()
        p.save(update_fields=["last_login"])
        super().at_post_login(session=session, **kwargs)

    def at_post_disconnect(self):
        """
        Modified to track logout time.
        """
        if not self.is_connected:
            p = self.playtime
            p.last_logout = utcnow()
            p.save(update_fields=["last_logout"])
        super().at_post_disconnect()

    def increment_playtime(self, value, characters):
        p = self.playtime
        p.total_playtime += value
        p.save(update_fields=["total_playtime"])
        self.at_total_playtime_update(p.total_playtime)

        for character in characters:
            c = character.playtime
            c.total_playtime += value
            c.save(update_fields=["total_playtime"])
            character.at_total_playtime_update(c.total_playtime)

            ca = c.per_account.get_or_create(account=self)[0]
            ca.total_playtime += value
            ca.save(update_fields=["total_playtime"])
            character.at_account_playtime_update(self, ca.total_playtime)

    def at_total_playtime_update(self, new_total: int):
        """
        This is called every time the total playtime is updated.
        """
        pass

    def get_playtime(self) -> int:
        """
        Returns the total playtime for this account.
        """
        return self.playtime.total_playtime
