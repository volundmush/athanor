# Output
This topic depends heavily on knowledge of [Evennia's Messagepath](https://www.evennia.com/docs/latest/Concepts/Messagepath.html) concepts (inputfuncs, outputfuncs, etc) as it heavily subverts and alters it in some ways.

# The Problem(TM)
Complex output like tables, character sheets, bulletin board posts, direct messages, channel messages, markdown blobs, and others must be sent as output to clients. However, characters may have connections from multiple kinds of clients that have different features. Telnet is extremely limited compared to webclients, for instance, and it would be a shame to limit webclients entirely to the vagaries of telnet-based MUD design. Evennia's inputfuncs and outputfuncs go a long way towards this, and Athanor takes it a step further.

# Athanor's Solution

## Formatters
To create complex data structures such as tables, athanor has default Formatter objects found in `athanor/formatters.py`. These are simple data-holding classes with a `.render()` method which is responsible for the simple act of turning the results of commands and operations into JSON or similar - primitive, serializable data structures that can be pickled or saved to a database safely.

Formatters may be used in place of string data or other values when using `.msg()` kwargs. for instance...

```python
from athanor.formatters import Table

t = Table(title="Example")
character.msg(table=t)
```

The new .msg() method will detect formatters and render them before moving on to further steps like logging or relaying to sessions. So, Formatters are meant to be used as a CONVENIENCE in place of defining the complex JSON directly.

## Renderers
When outgoing data reaches `ServerSession.data_out(**kwargs)`, the ServerSession will retrieve its dictionary of RENDERERS from `athanor.RENDERERS[<family>]`. If a renderer exists for a key (like "table", or "markdown", or "text"), then it will be called. The results may alter the given options, the outputfunc type (like turning "table" into "ansi" over telnet).

Since multiple kinds of messages might be rendered into the same kind of outputfunc, it is recommended to not call .msg() with multiple kwargs. Instead, call it once per message.

Example:
```python
character.msg(table=table)
character.msg(markdown=markdown)
```

Athanor determines which "family" of renderers to use based on the protocol_key of the Session (IE: telnet, telnet/tls, webclient/websocket, webclient/ajax, ssh, etc). The mapping is maintained in settings as the `PROTOCOL_RENDER_FAMILY` dictionary, which is loaded up with renderer funcs defined in `ATHANOR_RENDERER_MODULES` (a defaultdict(list)). This allows Renderers to be replaced by identical-named ones from later-listed modules.

Renderers DO NOT need to export just ansi colored text. They can export anything which can be sent out via Evennia's outputfunc path. This includes JSON, HTML, random binary encoded as base64, whatever.

## PortalSession send_* funcs
Each PortalSession can respond to outputfuncs by checking for a matching send_* method on that Protocol as data is being sent to the client. `protocol.send_text()` is used for standard Evennia text output. Athanor provides a method for 'ansi' which is largely a wrapper for sending raw colored text over telnet, or calling an ansi2html converter for the webclient. It's easy to add new send_* functions though and subclass protocol classes by altering settings.py.

## Output buffering and Results outputs.
Athanor has an `OutputBuffer` class in `athanor/utils.py` which captures .msg() calls meant to be sent to an object, account, or session, and can then unleash them all at once by flushing the buffer. This 'bundles' the messages into a single outgoing message. The bundle may have an attached "results_id" that will appear in its formatted kwargs.

## Matching input and Output
All AthanorCommands buffer their output by default. The buffer is flushed by the `at_post_cmd()` hook. The flush will, by default, use the results_id set on the command instance. This attribute can be set using the inputfunc's kwargs, a feat only accessible to the webclient and similar protocols. (telnet cannot do this unfortunately....)

For example,
`["text", ["look"], {"results_id": 5}]`
If the webclient sends this, it will get back a 'bundle' containing the response sent to cmd.msg() as the command runs, which is identified by results_id: 5. This allows the webclient to match up the output with the input.

This unfortunately cannot capture ALL possible outputs triggered by a command, such as alerts sent to other characters, alerts triggered by other components of Evennia, and error messages, nor is it guaranteed that a result WILL be sent.