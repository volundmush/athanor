import uuid
import typing
import random
import string
import yaml
import orjson
import re
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from django.conf import settings
from rest_framework import status
from evennia import SESSION_HANDLER
from evennia.utils.ansi import parse_ansi, ANSIString
from evennia.utils.evtable import EvTable


def read_json_file(p: Path):
    return orjson.loads(open(p, mode="rb").read())


def read_yaml_file(p: Path):
    return yaml.safe_load(open(p, mode="r"))


def read_data_file(p: Path):
    if p.name.lower().endswith(".json"):
        return read_json_file(p)
    elif p.name.lower().endswith(".yaml"):
        return read_yaml_file(p)
    return None


def fresh_uuid4(existing) -> uuid:
    """
    Given a list of UUID4s, generate a new one that's not already used.
    Yes, I know this is silly. UUIDs are meant to be unique by sheer statistic unlikelihood of a conflict.
    I'm just that afraid of collisions.
    """
    existing = set(existing)
    fresh_uuid = uuid.uuid4()
    while fresh_uuid in existing:
        fresh_uuid = uuid.uuid4()
    return fresh_uuid


def partial_match(
    match_text: str,
    candidates: typing.Iterable[typing.Any],
    key: callable = str,
    exact: bool = False,
    many_results: bool = False,
) -> typing.Optional[typing.Any]:
    """
    Given a list of candidates and a string to search for, does a case-insensitive partial name search against all
    candidates, preferring exact matches.

    Args:
        match_text (str): The string being searched for.
        candidates (list of obj): A list of any kind of object that key can turn into a string to search.
        key (callable): A callable that must return a string, used to do the search. this 'converts' the objects in the
            candidate list to strings.
        exact (bool): If True, only exact matches are returned.
        many_results (bool): If True, returns a list of all matches. If False, returns the first match.


    Returns:
        Any or None, or a list[Any]
    """
    mlow = match_text.lower()
    out = list()

    candidates_sorted = sorted((key(c).lower(), c) for c in candidates)

    for can_lower, candidate in candidates_sorted:
        if mlow == can_lower:
            if many_results:
                out.append(candidate)
            else:
                return candidate
        elif not exact and can_lower.startswith(mlow):
            if many_results:
                out.append(candidate)
            else:
                return candidate
    return out if many_results else None


def generate_name(prefix: str, existing, gen_length: int = 20) -> str:
    def gen():
        return f"{prefix}_{''.join(random.choices(string.ascii_letters + string.digits, k=gen_length))}"

    while (u := gen()) not in existing:
        return u


def iequals(first: str, second: str):
    return str(first).lower() == str(second).lower()


def utcnow():
    return datetime.now(timezone.utc)


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


RE_STAT_NAME = re.compile(r"^[a-zA-Z0-9_ \-,.']+$")


def validate_name(name: str, thing_type: str = "Stat", matcher=RE_STAT_NAME) -> str:
    """
    Cleans and validates a stat name for use in the system.
    This should strip/trim leading/trailing spaces and squish double spaces
    and only allow certain characters.

    Args:
        name (str): The input value.
        thing_type (str): The name of the type of thing being provided. used for errors.
        matcher (regex): The regex to match against.

    Returns:
        str: The cleaned name.

    Raises:
        ValueError: With the error message.
    """
    name = name.strip()
    # remove all double-spaces.
    while "  " in name:
        name = name.replace("  ", " ")
    if not name:
        raise ValueError(f"{thing_type} name cannot be empty.")
    if not matcher.match(name):
        raise ValueError(f"{thing_type} contains forbidden characters.")
    return name


def online_characters():
    return {sess.puppet for sess in SESSION_HANDLER.get_sessions() if sess.puppet}


def format_for_nobody(template: str, mapping: dict = None) -> str:
    if mapping is None:
        mapping = {}

    from evennia.objects.objects import _MSG_CONTENTS_PARSER

    outmessage = _MSG_CONTENTS_PARSER.parse(
        template,
        raise_errors=True,
        return_string=True,
        caller=None,
        receiver=None,
        mapping=mapping,
    )

    keys = SafeDict(
        {
            key: obj.get_display_name(looker=None)
            if hasattr(obj, "get_display_name")
            else str(obj)
            for key, obj in mapping.items()
        }
    )

    return ANSIString(outmessage.format_map(keys))


def staff_alert(message: str, senders=None):
    from evennia.comms.comms import DefaultChannel

    if not (channel := DefaultChannel.objects.filter(db_key=settings.ALERTS_CHANNEL).first()):
        return

    channel.msg(message, senders=senders)


def online_accounts():
    from evennia import SESSION_HANDLER
    return SESSION_HANDLER.all_connected_accounts()


def online_characters():
    from evennia import search_tag
    return search_tag(key="puppeted", category="account")


class RequestError(ValueError):
    pass


class Request:
    """
    Class used to handle requests against Athanor API objects to reduce boilerplate.
    """

    ex = RequestError
    st = status

    def __init__(self, target, **kwargs):
        self.target = target
        self.user: "DefaultAccount" = kwargs.pop("user", None)
        self.character: "DefaultCharacter" = kwargs.pop("character", None)
        self.operation: str = kwargs.pop("operation", None)
        self.kwargs: dict = kwargs.pop("kwargs", dict())
        self.extra: dict = kwargs
        self.status: status = status.HTTP_200_OK
        self.results = dict()
        self.system_name = getattr(self.target, "system_name", "SYSTEM")

    def error(self, message: str):
        """
        Send an error message to the user.
        """
        target = self.character or self.user
        target.system_send(
            getattr(self.target, "system_name", "SYSTEM"),
            message,
            mapping={},
            from_obj=target,
        )

    def execute(self):
        try:
            if not self.user:
                raise Exception("No user provided.")
            if not (method := getattr(self.target, f"op_{self.operation}", None)):
                raise Exception(f"No such operation: {self.operation}")
            if hasattr(self.target, "prepare_kwargs"):
                self.target.prepare_kwargs(self)
            method(self)
            self.results.update({"success": True})
        except self.ex as err:
            error = str(err)
            self.results.update({"success": False, "error": error, "message": error})
            return
        except Exception as err:
            error = f"{str(err)} (Something went very wrong. Please alert staff.)"
            self.results.update({"success": False, "error": error, "message": error})
            return
