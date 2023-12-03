# Output
This topic depends heavily on knowledge of [Evennia's Messagepath](https://www.evennia.com/docs/latest/Concepts/Messagepath.html) concepts (inputfuncs, outputfuncs, etc) as it heavily subverts and alters it in some ways.

# The Problem(TM)
Complex output like tables, character sheets, bulletin board posts, direct messages, channel messages, markdown blobs, and others must be sent as output to clients. However, characters may have connections from multiple kinds of clients that have different features. Telnet is extremely limited compared to webclients, for instance, and it would be a shame to limit webclients entirely to the vagaries of telnet-based MUD design. Evennia's inputfuncs and outputfuncs go a long way towards this, and Athanor takes it a step further.

# Athanor's Solution

## Formatters
To create complex data structures such as tables, athanor has default Formatter objects found in `athanor/formatters.py`. These are simple data-holding classes with a `.render()` method which is responsible for the simple act of turning the results of commands and operations into JSON or similar - primitive, serializable data structures that can be pickled or saved to a database safely.

Formatters may be used in place of string data or other values when using `.msg()` kwargs. for instance...

```python
from athanor.sendables import Table

t = Table(title="Example")
character.msg(table=t)
```

## Rendering Output
When outgoing data reaches `ServerSession.data_out(**kwargs)`, the ServerSession will use its `render_type` to attempt to render a Formatter. The `render_type` is determined by the `protocol_key` and a dictionary in `settings.py` called `PROTOCOL_RENDER_FAMILY`.

This determines whether `render_ansi`, `render_html`, or `render_json` is called, or potentially others added by developers.

These methods always take the session and the kwargs data, and will output a tuple of (str, args, kwargs) as the new outputfunc - the name of the outputfunc may even change.

Since multiple kinds of messages might be rendered into the same kind of outputfunc, it is recommended to not call .msg() with multiple kwargs. Instead, call it once per message.

Example:
```python
character.msg(table=table)
character.msg(markdown=markdown)
```

## PortalSession send_* funcs
Each PortalSession can respond to outputfuncs by checking for a matching send_* method on that Protocol as data is being sent to the client. `protocol.send_text()` is used for standard Evennia text output. Athanor provides a method for `send_ansi()` which is largely a wrapper for sending raw colored text over telnet, or calling an ansi2html converter for the webclient. It's easy to add new send_* functions though and subclass protocol classes by altering settings.py.

## Output buffering and Results outputs.
Athanor has an `OutputBuffer` class in `athanor/utils.py` which captures `.msg(**kwargs)` calls meant to be sent to an object, account, or session, and can then unleash them all at once by flushing the buffer. This 'bundles' the messages into a single outgoing message of the `results` output type. This message may have an attached "cmdid" that will appear in its formatted kwargs. its args is a list of outputfunc tuples in order that the kwargs were sent to `.msg()`.

## Matching input and Output
All AthanorCommands buffer their output by default. The buffer is flushed by the `at_post_cmd()` hook. The flush will, by default, use the results_id set on the command instance. This attribute can be set using the inputfunc's kwargs, a feat only accessible to the webclient and similar protocols. (telnet cannot do this unfortunately....)

For example,
`["text", ["look"], {"cmdid": 5}]`
If the webclient sends this, it will get back a 'bundle' containing the response sent to `cmd.msg()` as the command runs, which is identified by cmdid: 5. This allows the webclient to match up the output with the input.

This unfortunately cannot capture ALL possible outputs triggered by a command, such as alerts sent to other characters, alerts triggered by other components of Evennia, and error messages, nor is it guaranteed that a result WILL be sent.