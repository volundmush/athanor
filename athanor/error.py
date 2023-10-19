from evennia.commands.cmdhandler import logger, format_exc, _IN_GAME_ERRORS, _
from rich.console import Console, RenderResult, ConsoleOptions, ConsoleRenderable
from rich.theme import Theme
from pygments.token import Comment, Keyword, Name, Number, Operator, String
from pygments.token import Text as TextToken
from pygments.token import Token
from rich.style import Style
from rich.highlighter import ReprHighlighter
from rich.constrain import Constrain
from rich._loop import loop_last
from rich.panel import Panel
from rich.text import Text


def __rich_console__(
        self, console: Console, options: ConsoleOptions
) -> RenderResult:
    theme = self.theme
    background_style = theme.get_background_style()
    token_style = theme.get_style_for_token

    traceback_theme = Theme(
        {
            "pretty": token_style(TextToken),
            "pygments.text": token_style(Token),
            "pygments.string": token_style(String),
            "pygments.function": token_style(Name.Function),
            "pygments.number": token_style(Number),
            "repr.indent": token_style(Comment) + Style(dim=True),
            "repr.str": token_style(String),
            "repr.brace": token_style(TextToken) + Style(bold=True),
            "repr.number": token_style(Number),
            "repr.bool_true": token_style(Keyword.Constant),
            "repr.bool_false": token_style(Keyword.Constant),
            "repr.none": token_style(Keyword.Constant),
            "scope.border": token_style(String.Delimiter),
            "scope.equals": token_style(Operator),
            "scope.key": token_style(Name),
            "scope.key.special": token_style(Name.Constant) + Style(dim=True),
        },
        inherit=False,
    )

    highlighter = ReprHighlighter()
    for last, stack in loop_last(reversed(self.trace.stacks)):
        if stack.frames:
            stack_renderable: ConsoleRenderable = Panel(
                self._render_stack(stack),
                title="[traceback.title]Traceback [dim](most recent call last)",
                style=background_style,
                border_style="traceback.border",
                expand=True,
                padding=(0, 1),
                box=self.box
            )
            stack_renderable = Constrain(stack_renderable, self.width)
            with console.use_theme(traceback_theme):
                yield stack_renderable
        if stack.syntax_error is not None:
            with console.use_theme(traceback_theme):
                yield Constrain(
                    Panel(
                        self._render_syntax_error(stack.syntax_error),
                        style=background_style,
                        border_style="traceback.border.syntax_error",
                        expand=True,
                        padding=(0, 1),
                        width=self.width,
                        box=self.box
                    ),
                    self.width,
                )
            yield Text.assemble(
                (f"{stack.exc_type}: ", "traceback.exc_type"),
                highlighter(stack.syntax_error.msg),
            )
        elif stack.exc_value:
            yield Text.assemble(
                (f"{stack.exc_type}: ", "traceback.exc_type"),
                highlighter(stack.exc_value),
            )
        else:
            yield Text.assemble((f"{stack.exc_type}", "traceback.exc_type"))

        if not last:
            if stack.is_cause:
                yield Text.from_markup(
                    "\n[i]The above exception was the direct cause of the following exception:\n",
                )
            else:
                yield Text.from_markup(
                    "\n[i]During handling of the above exception, another exception occurred:\n",
                )


def _msg_err(receiver, stringtuple):
    """
    Helper function for returning an error to the caller.

    Args:
        receiver (Object): object to get the error message.
        stringtuple (tuple): tuple with two strings - one for the
            _IN_GAME_ERRORS mode (with the traceback) and one with the
            production string (with a timestamp) to be shown to the user.

    """
    string = _("{traceback}\n{errmsg}\n(Traceback was logged {timestamp}).")
    timestamp = logger.timeformat()
    tracestring = format_exc()
    logger.log_trace()
    if _IN_GAME_ERRORS:
        receiver.msg(traceback=True)
    else:
        receiver.msg(
            string.format(
                traceback=tracestring.splitlines()[-1],
                errmsg=stringtuple[1].strip(),
                timestamp=timestamp,
            ).strip()
        )


