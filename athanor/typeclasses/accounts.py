import math
import datetime

from django.conf import settings
from django.utils.translation import gettext as _
from evennia.accounts.accounts import DefaultAccount, CharactersHandler
from evennia.utils import lazy_property, class_from_module, make_iter, dedent
from evennia.utils.ansi import ANSIString
from evennia.utils.evtable import EvTable
from evennia.server import signals
from rich.table import Table
from rich.box import ASCII2

import athanor
from athanor.utils import utcnow
from .mixin import AthanorLowBase, AthanorHandler

_CMDHANDLER = None


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
            owner.account = self.owner
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
    lock_default_funcs = settings.ACCOUNT_DEFAULT_LOCKS
    _content_types = ("account",)
    playview_typeclass = settings.BASE_PLAYVIEW_TYPECLASS

    # Determines which order command sets begin to be assembled from.
    # Accounts are usually second.
    cmd_order = 50
    cmd_order_error = 0
    cmd_type = "account"

    def get_command_objects(self) -> dict[str, "CommandObject"]:
        """
        Overrideable method which returns a dictionary of all the kinds of CommandObjects
        linked to this Account.
        In all normal cases, that's just the account itself.
        The cmdhandler uses this to determine available cmdsets when executing a command.
        Returns:
            dict[str, CommandObject]: The CommandObjects linked to this Account.
        """
        return {"account": self}

    def at_cmdset_get(self, **kwargs):
        """
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it. This is called also if the object currently
        have no cmdsets.
        Keyword Args:
            caller (obj): The object requesting the cmdsets.
            current (cmdset): The current merged cmdset.
            force_init (bool): If `True`, force a re-build of the cmdset. (seems unused)
            **kwargs: Arbitrary input for overloads.
        """
        pass

    def get_cmdsets(self, caller, current, **kwargs):
        """
        Called by the CommandHandler to get a list of cmdsets to merge.
        Args:
            caller (obj): The object requesting the cmdsets.
            current (cmdset): The current merged cmdset.
            **kwargs: Arbitrary input for overloads.
        Returns:
            tuple: A tuple of (current, cmdsets), which is probably self.cmdset.current and self.cmdset.cmdset_stack
        """
        return self.cmdset.current, list(self.cmdset.cmdset_stack)

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

    def check_character_count(self, session) -> bool:
        count = self.playviews.count()
        max_puppets = settings.MAX_NR_SIMULTANEOUS_PUPPETS
        if settings.MULTISESSION_MODE >= 2:
            if self.is_superuser or self.check_permstring("Developer"):
                return True
        else:
            max_puppets = 1
        if count > max_puppets:
            session.msg(f"You cannot control any more characters (max {max_puppets})")
            return False
        return not count

    def puppet_object(self, session, obj):
        """
        Use the given session to control (puppet) the given object (usually
        a Character type).

        Args:
            session (Session): session to use for puppeting
            obj (Object): the object to start puppeting

        Raises:
            RuntimeError: If puppeting is not possible, the
                `exception.msg` will contain the reason.


        """
        # safety checks
        if not obj:
            raise RuntimeError("Object not found")
        if not session:
            raise RuntimeError("Session not found")
        if getattr(session, "playview", None):
            # already puppeting this object
            session.msg("This session is already puppeting a character.")
            return
        if not obj.access(self, "puppet"):
            # no access
            session.msg(f"You don't have permission to puppet '{obj.key}'.")
            return

        if playview := getattr(obj, "playview", None):
            if self != obj.playview.account:
                session.msg(
                    f"{obj.playview.account} is currently logged in as {obj.key}."
                )
        else:
            if not self.check_character_count(session):
                return
            playview_class = class_from_module(self.playview_typeclass)
            playview = playview_class.create(self, obj)

        playview.add_session(session)

    def unpuppet_object(self, session):
        """
        Disengage control over an object.

        Args:
            session (Session or list): The session or a list of
                sessions to disengage from their puppets.

        Raises:
            RuntimeError With message about error.

        """
        for session in make_iter(session):
            obj = session.puppet
            if obj:
                playview = obj.playview
                playview.remove_session(session)

    ooc_appearance_template = dedent(
        """
    {header}

    {sessions}

    {commands}

    {characters}
    
    {footer}
    """
    ).strip()

    def at_look_header(self, session=None, **kwargs):
        return self.styled_header(f"Account Menu: {self.key}")

    def at_look_sessions(self, session=None, **kwargs):
        sessions = self.sessions.all()
        if not sessions:
            return ""

        sess_strings = []
        for isess, sess in enumerate(sessions):
            ip_addr = (
                sess.address[0] if isinstance(sess.address, tuple) else sess.address
            )
            addr = f"{sess.protocol_key} ({ip_addr})"
            sess_str = (
                f"|w* {isess + 1}|n"
                if session and session.sessid == sess.sessid
                else f"  {isess + 1}"
            )

            sess_strings.append(f"{sess_str} {addr}")

        return "|wConnected session(s):|n\n" + "\n".join(sess_strings)

    def at_look_commands(self, session=None, **kwargs):
        out = list()
        for cmd, desc in (
            ("|whelp|n", "more commands"),
            ("|wpublic <text>|n", "talk on public channel"),
            ("|wcharcreate <name> [=description]|n", "create new character"),
            ("|wchardelete <name>|n", "delete a character"),
            ("|wic <name>|n", "enter the game as character (|wooc|n to get back here)"),
            ("|wic|n", "enter the game as latest character controlled."),
        ):
            out.append(f"  {cmd} - {desc}")

        return "\n".join(out)

    def at_look_footer(self, session=None, **kwargs):
        return str(self.styled_footer())

    def at_look_characters(self, session=None, **kwargs):
        characters = self.characters.all()
        sessions = self.sessions.all()

        if not characters:
            txt_characters = "You don't have a character yet. Use |wcharcreate|n."
        else:
            max_chars = (
                "unlimited"
                if self.is_superuser or settings.MAX_NR_CHARACTERS is None
                else settings.MAX_NR_CHARACTERS
            )

            char_strings = []
            for char in characters:
                csessions = char.sessions.all()
                if csessions:
                    for sess in csessions:
                        # character is already puppeted
                        sid = sess in sessions and sessions.index(sess) + 1
                        if sess and sid:
                            char_strings.append(
                                f" - |G{char.name}|n [{', '.join(char.permissions.all())}] "
                                f"(played by you in session {sid})"
                            )
                        else:
                            char_strings.append(
                                f" - |R{char.name}|n [{', '.join(char.permissions.all())}] "
                                "(played by someone else)"
                            )
                else:
                    # character is "free to puppet"
                    char_strings.append(
                        f" - {char.name} [{', '.join(char.permissions.all())}]"
                    )

            return (
                f"Available character(s) ({len(characters)}/{max_chars}, |wic <name>|n to play):|n\n"
                + "\n".join(char_strings)
            )

    def at_look(self, session=None, **kwargs):
        """
        Called when this object executes a look. It allows to customize
        just what this means.

        Args:
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)

        """
        sections = dict()
        for section in ("header", "sessions", "commands", "characters", "footer"):
            sections[section] = str(
                getattr(self, f"at_look_{section}")(session=session, **kwargs)
            )

        return self.ooc_appearance_template.format_map(sections)

    def at_account_creation(self):
        if not self.is_superuser:
            self.locks.clear()

    def execute_cmd(self, raw_string, session=None, **kwargs):
        """
        Do something as this account. This method is never called normally,
        but only when the account object itself is supposed to execute the
        command. It takes account nicks into account, but not nicks of
        eventual puppets.

        Args:
            raw_string (str): Raw command input coming from the command line.
            session (Session, optional): The session to be responsible
                for the command-send

        Keyword Args:
            kwargs (any): Other keyword arguments will be added to the
                found command object instance as variables before it
                executes. This is unused by default Evennia but may be
                used to set flags and change operating parameters for
                commands at run-time.

        """
        # break circular import issues
        global _CMDHANDLER
        if not _CMDHANDLER:
            from athanor.cmdhandler import cmdhandler as _CMDHANDLER
        raw_string = self.nicks.nickreplace(
            raw_string, categories=("inputline", "channel"), include_account=False
        )
        if not session and settings.MULTISESSION_MODE in (0, 1):
            # for these modes we use the first/only session
            sessions = self.sessions.get()
            session = sessions[0] if sessions else None

        return _CMDHANDLER(
            self, raw_string, callertype="account", session=session, **kwargs
        )
