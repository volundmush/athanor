import ipaddress
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
from rich.text import Text
from rich.ansi import AnsiDecoder
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


def validate_name(
    name: str,
    thing_type: str = "Stat",
    matcher=RE_STAT_NAME,
    ex_type: Exception = ValueError,
) -> str:
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
        raise ex_type(f"{thing_type} name cannot be empty.")
    if not matcher.match(name):
        raise ex_type(f"{thing_type} contains forbidden characters.")
    return name


def online_characters():
    from .playviews import DefaultPlayview

    return {playview.id for playview in DefaultPlayview.objects.all()}


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

    if not (
        channel := DefaultChannel.objects.filter_family(
            db_key=settings.ALERTS_CHANNEL
        ).first()
    ):
        return

    channel.msg(message, senders=senders)


def online_accounts():
    from evennia import SESSION_HANDLER

    return SESSION_HANDLER.all_connected_accounts()


def online_characters():
    from evennia import search_tag

    return search_tag(key="puppeted", category="account")


class OperationError(ValueError):
    pass


class Operation:
    """
    Class used to handle requests against Athanor API objects to reduce boilerplate.

    This is available in convenience wrapper form in AthanorCommand as self.operation, which
    automates filling out the user and character kwargs.
    """

    ex = OperationError
    st = status

    def __init__(self, target, **kwargs):
        """
        Create the Operation object.
        """
        # The target is the object which is being operated on.
        # it must have methods that match the pattern op_<operation>, like op_create.
        # These methods must take a single argument, the operation object.
        self.target = target

        # The user and character are the user and character who initiated the operation.
        # This will be used for permissions checks and logs.
        self.user: "DefaultAccount" = kwargs.pop("user", None)
        self.character: "DefaultCharacter" = kwargs.pop("character", None)

        # The operation that will be called on the target. This must be a string.
        self.operation: str = kwargs.pop("operation", None)

        # Arbitrary variables available to the operation.
        self.kwargs: dict = kwargs.pop("kwargs", dict())

        # The HTTP response code to return to the user. This is relevant only for
        # web views.
        self.status: status = status.HTTP_200_OK

        # The results of the operation. This is a dictionary that is accessible
        # after the operation.
        self.results = dict()

        # Used for formatting some messages.
        self.system_name = getattr(self.target, "system_name", "SYSTEM")

        # A convenience variable of accessing (character or user), usually used for
        # lock checks.
        self.actor = self.character or self.user

        # Used as scratch space by the operation, if needed.
        self.variables = dict()

    def execute(self):
        try:
            if not self.user:
                raise Exception("No user provided.")
            if not (method := getattr(self.target, f"op_{self.operation}", None)):
                raise Exception(f"No such operation: {self.operation}")
            if hasattr(self.target, "at_pre_operation"):
                self.target.at_pre_operation(self)
            method(self)
            self.results.update({"success": True})
            if hasattr(self.target, "at_post_operation"):
                self.target.at_post_operation(self)
        except self.ex as err:
            error = str(err)
            self.results.update({"success": False, "error": True, "message": error})
        except Exception as err:
            error = f"{str(err)} (Something went very wrong. Please alert staff.)"
            self.results.update({"success": False, "error": True, "message": error})
            if settings.IN_GAME_ERRORS:
                self.actor.msg(traceback=True)


def ev_to_rich(text: str):
    """
    Converts an Evennia ANSIString to a Rich Text.
    """
    ev = parse_ansi(str(text), xterm256=True, mxp=True)
    return Text("\n").join(AnsiDecoder().decode(ev))


def register_access_functions(access_types: list[str]):
    from evennia.utils import class_from_module
    from django.conf import settings
    import athanor

    for t in access_types:
        access_funcs = f"{t}_ACCESS_FUNCTIONS"
        access_funcs_from = getattr(settings, access_funcs)
        access_funcs_to = getattr(athanor, access_funcs)

        for access_type, func_list in access_funcs_from.items():
            for func_path in func_list:
                access_funcs_to[access_type].append(class_from_module(func_path))


def register_lock_functions(types: list[str]):
    from evennia.utils import class_from_module
    from django.conf import settings
    import athanor

    for t in types:
        default_locks = f"{t}_DEFAULT_LOCKS"
        default_locks_from = getattr(settings, default_locks)
        default_locks_to = getattr(athanor, default_locks)

        for access_type, func_list in default_locks_from.items():
            for func_path in func_list:
                if "(" in func_path:
                    # this is a literal lockstring. Add it directly.
                    default_locks_to[access_type].append(func_path)
                else:
                    default_locks_to[access_type].append(class_from_module(func_path))


def match_ip(address, pattern) -> bool:
    """
    Check if an IP address matches a given pattern. The pattern can be a single IP address
    such as 8.8.8.8 or a CIDR-formatted subnet like 10.0.0.0/8

    IPv6 is supported to, with CIDR-subnets looking like 2001:db8::/48

    Args:
        address (str): The source address being checked.
        pattern (str): The single IP address or subnet to check against.

    Returns:
        result (bool): Whether it was a match or not.
    """
    try:
        # Convert the given IP address to an IPv4Address or IPv6Address object
        ip_obj = ipaddress.ip_address(address)
    except ValueError:
        # Invalid IP address format
        return False

    try:
        # Check if pattern is a single IP or a subnet
        if "/" in pattern:
            # It's (hopefully) a subnet in CIDR notation
            network = ipaddress.ip_network(pattern, strict=False)
            if ip_obj in network:
                return True
        else:
            # It's a single IP address
            if ip_obj == ipaddress.ip_address(pattern):
                return True
    except ValueError:
        return False
    return False


def ip_from_request(request, exclude=None) -> str:
    """
    Retrieves the IP address from a Django Request, while respecting X-Forwarded-For and
    settings.UPSTREAM_IPS.

    Args:
        request (django Request): The web request.
        exclude: (list, optional): A list of IP addresses to exclude from the check. If left none,
            then settings.UPSTREAM_IPS will be used.

    Returns:
        ip (str): The IP address the request originated from.
    """
    if exclude is None:
        exclude = settings.UPSTREAM_IPS
    remote_addr = request.getClientIP()
    addresses = list()
    addresses.append(remote_addr)

    if forwarded := request.getHeader("x-forwarded-for"):
        addresses.extend(x.strip() for x in forwarded.split(","))

    for addr in reversed(addresses):
        if all(not match_ip(addr, pattern) for pattern in exclude):
            return addr

    logger.log_warn(
        "ip_from_request: No valid IP address found in request. Using remote_addr."
    )
    return remote_addr


def increment_playtime():
    from .playviews import DefaultPlayview

    accounts = defaultdict(list)

    for account in online_accounts():
        accounts[account] = list()

    for playview in DefaultPlayview.objects.all():
        accounts[playview].append(playview.id)

    for account, characters in accounts.items():
        account.increment_playtime(settings.PLAYTIME_INTERVAL, characters)
