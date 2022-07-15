import uuid
import typing
import random
import string
import yaml
import orjson
from datetime import datetime, timezone

from pathlib import Path
from evennia.utils.ansi import parse_ansi, ANSIString
from rich.ansi import AnsiDecoder
from rich.console import group

from collections import defaultdict



def read_json_file(p: Path):
    return orjson.loads(open(p, mode='rb').read())


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
    match_text: str, candidates: typing.Iterable[typing.Any], key: callable = str, exact: bool = False) -> typing.Optional[typing.Any]:
    """
    Given a list of candidates and a string to search for, does a case-insensitive partial name search against all
    candidates, preferring exact matches.

    Args:
        match_text (str): The string being searched for.
        candidates (list of obj): A list of any kind of object that key can turn into a string to search.
        key (callable): A callable that must return a string, used to do the search. this 'converts' the objects in the
            candidate list to strings.

    Returns:
        Any or None.
    """
    candidate_list = sorted(candidates, key=lambda item: len(key(item)))
    mlow = match_text.lower()
    for candidate in candidate_list:
        can_lower = key(candidate).lower()
        if mlow == can_lower:
            return candidate
        if not exact:
            if can_lower.startswith(mlow):
                return candidate


def generate_name(prefix: str, existing, gen_length: int = 20) -> str:
    def gen():
        return f"{prefix}_{''.join(random.choices(string.ascii_letters + string.digits, k=gen_length))}"

    while (u := gen()) not in existing:
        return u


@group()
def ev_to_rich(s: str):
    if isinstance(s, ANSIString):
        for line in AnsiDecoder().decode(str(s)):
            yield line
    else:
        ev = parse_ansi(s, xterm256=True, mxp=True)
        for line in AnsiDecoder().decode(ev):
            yield line


def echo_action(template: str, actors: dict[str, "DefaultObject"], viewers: typing.Iterable["DefaultObject"], **kwargs):

    for viewer in viewers:
        var_dict = defaultdict(lambda: "!ERR!")
        var_dict.update(kwargs)
        for k, v in actors.items():
            v.get_template_vars(var_dict, k, looker=viewer)

        viewer.msg(text=ev_to_rich(template.format_map(var_dict)))


def iequals(first: str, second: str):
    return str(first).lower() == str(second).lower()


def utcnow():
    return datetime.now(timezone.utc)


