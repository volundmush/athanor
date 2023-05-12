from rich.color import ColorSystem
from django.conf import settings
from evennia.server.sessionhandler import ServerSessionHandler, codecs_decode, _ERR_BAD_UTF8,\
    _FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED, is_iter
from evennia.server.serversession import ServerSession
from evennia.utils.utils import lazy_property, logger

_FUNCPARSER = None

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorServerSessionHandler(ServerSessionHandler):
    def clean_senddata(self, session, kwargs):
        """
        Clean up data for sending across the AMP wire. Also apply the
        FuncParser using callables from `settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES`.

        Args:
            session (Session): The relevant session instance.
            kwargs (dict) Each keyword represents a send-instruction, with the keyword itself being
                the name of the instruction (like "text"). Suitable values for each keyword are:
                - arg                ->  [[arg], {}]
                - [args]             ->  [[args], {}]
                - {kwargs}           ->  [[], {kwargs}]
                - [args, {kwargs}]   ->  [[arg], {kwargs}]
                - [[args], {kwargs}] ->  [[args], {kwargs}]

        Returns:
            kwargs (dict): A cleaned dictionary of cmdname:[[args],{kwargs}] pairs,
            where the keys, args and kwargs have all been converted to
            send-safe entities (strings or numbers), and funcparser parsing has been
            applied.

        """

        global _FUNCPARSER
        if not _FUNCPARSER:
            from evennia.utils.funcparser import FuncParser

            _FUNCPARSER = FuncParser(
                settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES, raise_errors=True
            )

        options = kwargs.pop("options", None) or {}
        raw = options.get("raw", False)
        strip_inlinefunc = options.get("strip_inlinefunc", False)

        def _utf8(data):
            if isinstance(data, bytes):
                try:
                    data = codecs_decode(data, session.protocol_flags["ENCODING"])
                except LookupError:
                    # wrong encoding set on the session. Set it to a safe one
                    session.protocol_flags["ENCODING"] = "utf-8"
                    data = codecs_decode(data, "utf-8")
                except UnicodeDecodeError:
                    # incorrect unicode sequence
                    session.sendLine(_ERR_BAD_UTF8)
                    data = ""

            return data

        def _validate(data):
            """
            Helper function to convert data to AMP-safe (picketable) values"

            """
            if hasattr(data, "__rich_console__"):
                return data
            elif isinstance(data, dict):
                newdict = {}
                for key, part in data.items():
                    newdict[key] = _validate(part)
                return newdict
            elif is_iter(data):
                return [_validate(part) for part in data]
            elif isinstance(data, (str, bytes)):
                data = _utf8(data)

                if (
                    _FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED
                    and not raw
                    and isinstance(self, ServerSessionHandler)
                ):
                    # only apply funcparser on the outgoing path (sessionhandler->)
                    # data = parse_inlinefunc(data, strip=strip_inlinefunc, session=session)
                    data = _FUNCPARSER.parse(data, strip=strip_inlinefunc, session=session)

                return str(data)
            elif (
                hasattr(data, "id")
                and hasattr(data, "db_date_created")
                and hasattr(data, "__dbclass__")
            ):
                # convert database-object to their string representation.
                return _validate(str(data))
            else:
                return data

        rkwargs = {}
        for key, data in kwargs.items():
            key = _validate(key)
            if not data:
                if key == "text":
                    # we don't allow sending text = None, this must mean
                    # that the text command is not to be used.
                    continue
                rkwargs[key] = [[], {}]
            elif isinstance(data, dict):
                rkwargs[key] = [[], _validate(data)]
            elif hasattr(data, "__rich_console__"):
                rkwargs[key] = [[data, ], {}]
            elif is_iter(data):
                data = tuple(data)
                if isinstance(data[-1], dict):
                    if len(data) == 2:
                        if is_iter(data[0]):
                            rkwargs[key] = [_validate(data[0]), _validate(data[1])]
                        else:
                            rkwargs[key] = [[_validate(data[0])], _validate(data[1])]
                    else:
                        rkwargs[key] = [_validate(data[:-1]), _validate(data[-1])]
                else:
                    rkwargs[key] = [_validate(data), {}]
            else:
                rkwargs[key] = [[_validate(data)], {}]
            rkwargs[key][1]["options"] = dict(options)
        # make sure that any "prompt" message will be processed last
        # by moving it to the end
        if "prompt" in rkwargs:
            prompt = rkwargs.pop("prompt")
            rkwargs["prompt"] = prompt
        return rkwargs
