"""
Athanor's command parser. implements a partial match logic. Largely copied from Evennia 1.0-dev.

`settings.COMMAND_PARSER` to a Python path to a module containing the
replacing cmdparser function. The replacement parser must accept the
same inputs as the default one.

"""


import re
from django.conf import settings
from evennia.utils.logger import log_trace

_MULTIMATCH_REGEX = re.compile(settings.SEARCH_MULTIMATCH_REGEX, re.I + re.U)
_CMD_IGNORE_PREFIXES = settings.CMD_IGNORE_PREFIXES


def create_match(cmdname, string, cmdobj, raw_cmdname):
    """
    Builds a command match by splitting the incoming string and
    evaluating the quality of the match.

    Args:
        cmdname (str): Name of command to check for.
        string (str): The string to match against.
        cmdobj (str): The full Command instance.
        raw_cmdname (str, optional): If CMD_IGNORE_PREFIX is set and the cmdname starts with
            one of the prefixes to ignore, this contains the raw, unstripped cmdname,
            otherwise it is None.

    Returns:
        match (tuple): This is on the form (cmdname, args, cmdobj, cmdlen, mratio, raw_cmdname),
            where `cmdname` is the command's name and `args` is the rest of the incoming
            string, without said command name. `cmdobj` is
            the Command instance, the cmdlen is the same as len(cmdname) and mratio
            is a measure of how big a part of the full input string the cmdname
            takes up - an exact match would be 1.0. Finally, the `raw_cmdname` is
            the cmdname unmodified by eventual prefix-stripping.

    """
    cmdlen, strlen = len(str(cmdname)), len(str(string))
    mratio = 1 - (strlen - cmdlen) / (1.0 * strlen)
    args = string[cmdlen:]
    return (cmdname, args, cmdobj, cmdlen, mratio, raw_cmdname)


def build_matches(raw_string, cmd_args, cmdset, include_prefixes=False):
    """
    Build match tuples by matching raw_string against available commands.

    Args:
        raw_string (str): Input string that can look in any way; the only assumption is
            that the sought command's name/alias must be *first* in the string.
        cmdset (CmdSet): The current cmdset to pick Commands from.
        include_prefixes (bool): If set, include prefixes like @, ! etc (specified in settings)
            in the match, otherwise strip them before matching.

    Returns:
        matches (list) A list of match tuples created by `cmdparser.create_match`.

    """
    matches = []
    cmd_dict = []
    for cmd in cmdset:
        if cmd.key and isinstance(cmd.key, str):
            cmd_dict[cmd.key] = cmd
        for a in cmd.aliases:
            cmd_dict[a] = cmd

    try:
        if include_prefixes:
            # use the cmdname as-is
            l_raw_string = raw_string.lower()
            matches.extend([create_match(cmdname, raw_string, cmd, cmdname)] for cmdname, cmd in cmd_dict.items())
            for cmdname, cmd in cmd_dict.items():

                matches.extend(
                    [
                        create_match(cmdname, raw_string, v, cmdname)
                        for cmdname in [cmd.key] + cmd.aliases
                        if cmdname
                        and l_raw_string.startswith(cmdname.lower())
                        and (not cmd.arg_regex or cmd.arg_regex.match(l_raw_string[len(cmdname) :]))
                    ]
                )
            if not
        else:
            # strip prefixes set in settings
            raw_string = (
                raw_string.lstrip(_CMD_IGNORE_PREFIXES) if len(raw_string) > 1 else raw_string
            )
            l_raw_string = raw_string.lower()
            for cmd in cmdset:
                for raw_cmdname in [cmd.key] + cmd.aliases:
                    cmdname = (
                        raw_cmdname.lstrip(_CMD_IGNORE_PREFIXES)
                        if len(raw_cmdname) > 1
                        else raw_cmdname
                    )
                    if (
                        cmdname
                        and l_raw_string.startswith(cmdname.lower())
                        and (not cmd.arg_regex or cmd.arg_regex.match(l_raw_string[len(cmdname) :]))
                    ):
                        matches.append(create_match(cmdname, raw_string, cmd, raw_cmdname))
    except Exception:
        log_trace("cmdhandler error. raw_input:%s" % raw_string)
    return matches


def cmdparser(raw_string, cmdset, caller, match_index=None):
    """
    This function is called by the cmdhandler once it has
    gathered and merged all valid cmdsets valid for this particular parsing.

    Args:
        raw_string (str): The unparsed text entered by the caller.
        cmdset (CmdSet): The merged, currently valid cmdset
        caller (Session, Account or Object): The caller triggering this parsing.
        match_index (int, optional): Index to pick a given match in a
            list of same-named command matches. If this is given, it suggests
            this is not the first time this function was called: normally
            the first run resulted in a multimatch, and the index is given
            to select between the results for the second run.

    Returns:
        matches (list): This is a list of match-tuples as returned by `create_match`.
            If no matches were found, this is an empty list.

    Notes:
        The cmdparser understand the following command combinations (where
        [] marks optional parts.

        ```
        [cmdname[ cmdname2 cmdname3 ...] [the rest]
        ```

        A command may consist of any number of space-separated words of any
        length, and contain any character. It may also be empty.

        The parser makes use of the cmdset to find command candidates. The
        parser return a list of matches. Each match is a tuple with its
        first three elements being the parsed cmdname (lower case),
        the remaining arguments, and the matched cmdobject from the cmdset.

    """
    if not raw_string:
        return []

    if not (m := _MULTIMATCH_REGEX.match(raw_string)):
        return []
    cmd_string = m.group("name")
    cmd_number = m.group("number")
    cmd_args = m.group("args")
    if cmd_number is None:
        cmd_number = "1"
    elif cmd_number.lower() in ("all", "*"):
        cmd_number = "1"
    match_index = int(cmd_number)-1

    # find matches
    matches = build_matches(cmd_string, cmd_args, cmdset, include_prefixes=True)

    if not matches and _CMD_IGNORE_PREFIXES:
        # still no match. Try to strip prefixes
        raw_string = cmd_string.lstrip(_CMD_IGNORE_PREFIXES) if len(raw_string) > 1 else raw_string
        matches = build_matches(raw_string, cmdset, include_prefixes=False)

    # only select command matches we are actually allowed to call.
    matches = [match for match in matches if match[2].access(caller, "cmd")]

    # try to bring the number of matches down to 1
    if len(matches) > 1:
        # See if it helps to analyze the match with preserved case but only if
        # it leaves at least one match.
        trimmed = [match for match in matches if cmd_string.startswith(match[0])]
        if trimmed:
            matches = trimmed

    if len(matches) > 1:
        # we still have multiple matches. Sort them by count quality.
        matches = sorted(matches, key=lambda m: m[3])
        # only pick the matches with highest count quality
        quality = [mat[3] for mat in matches]
        matches = matches[-quality.count(quality[-1]) :]

    if len(matches) > 1:
        # still multiple matches. Fall back to ratio-based quality.
        matches = sorted(matches, key=lambda m: m[4])
        # only pick the highest rated ratio match
        quality = [mat[4] for mat in matches]
        matches = matches[-quality.count(quality[-1]) :]

    if len(matches) > 1 and match_index is not None:
        # We couldn't separate match by quality, but we have an
        # index argument to tell us which match to use.
        if 0 < match_index <= len(matches):
            matches = [matches[match_index - 1]]
        else:
            # we tried to give an index outside of the range - this means
            # a no-match
            matches = []

    # no matter what we have at this point, we have to return it.
    return matches
