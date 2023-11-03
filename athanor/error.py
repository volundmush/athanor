import os
from evennia.commands.cmdhandler import logger, format_exc, _IN_GAME_ERRORS, _
from rich.console import Console, RenderResult, ConsoleOptions, ConsoleRenderable, group
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
from rich.traceback import (
    Traceback,
    PathHighlighter,
    render_scope,
    Stack,
    linecache,
    Frame,
)
from rich.traceback import Iterable, Columns, Syntax, Optional


class AthanorTraceback(Traceback):
    @group()
    def _render_stack(self, stack: Stack) -> RenderResult:
        path_highlighter = PathHighlighter()
        theme = self.theme

        def read_code(filename: str) -> str:
            """Read files, and cache results on filename.

            Args:
                filename (str): Filename to read

            Returns:
                str: Contents of file
            """
            return "".join(linecache.getlines(filename))

        def render_locals(frame: Frame) -> Iterable[ConsoleRenderable]:
            if frame.locals:
                sc = render_scope(
                    frame.locals,
                    title="locals",
                    indent_guides=self.indent_guides,
                    max_length=self.locals_max_length,
                    max_string=self.locals_max_string,
                )
                sc.box = self.box
                yield sc

        exclude_frames: Optional[range] = None
        if self.max_frames != 0:
            exclude_frames = range(
                self.max_frames // 2,
                len(stack.frames) - self.max_frames // 2,
            )

        excluded = False
        for frame_index, frame in enumerate(stack.frames):
            if exclude_frames and frame_index in exclude_frames:
                excluded = True
                continue

            if excluded:
                assert exclude_frames is not None
                yield Text(
                    f"\n... {len(exclude_frames)} frames hidden ...",
                    justify="center",
                    style="traceback.error",
                )
                excluded = False

            first = frame_index == 0
            frame_filename = frame.filename
            suppressed = any(frame_filename.startswith(path) for path in self.suppress)

            if os.path.exists(frame.filename):
                text = Text.assemble(
                    path_highlighter(Text(frame.filename, style="pygments.string")),
                    (":", "pygments.text"),
                    (str(frame.lineno), "pygments.number"),
                    " in ",
                    (frame.name, "pygments.function"),
                    style="pygments.text",
                )
            else:
                text = Text.assemble(
                    "in ",
                    (frame.name, "pygments.function"),
                    (":", "pygments.text"),
                    (str(frame.lineno), "pygments.number"),
                    style="pygments.text",
                )
            if not frame.filename.startswith("<") and not first:
                yield ""
            yield text
            if frame.filename.startswith("<"):
                yield from render_locals(frame)
                continue
            if not suppressed:
                try:
                    code = read_code(frame.filename)
                    if not code:
                        # code may be an empty string if the file doesn't exist, OR
                        # if the traceback filename is generated dynamically
                        continue
                    lexer_name = self._guess_lexer(frame.filename, code)
                    syntax = Syntax(
                        code,
                        lexer_name,
                        theme=theme,
                        line_numbers=True,
                        line_range=(
                            frame.lineno - self.extra_lines,
                            frame.lineno + self.extra_lines,
                        ),
                        highlight_lines={frame.lineno},
                        word_wrap=self.word_wrap,
                        code_width=88,
                        indent_guides=self.indent_guides,
                        dedent=False,
                    )
                    yield ""
                except Exception as error:
                    yield Text.assemble(
                        (f"\n{error}", "traceback.error"),
                    )
                else:
                    yield (
                        Columns(
                            [
                                syntax,
                                *render_locals(frame),
                            ],
                            padding=1,
                        )
                        if frame.locals
                        else syntax
                    )

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
                    box=self.box,
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
                            box=self.box,
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
