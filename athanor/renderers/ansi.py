from rich.table import Table
from rich.box import ASCII2
from rich.markdown import Markdown
from rich.highlighter import ReprHighlighter
from athanor.error import AthanorTraceback


def table(session, data, options):

    kwargs = {
        "box": ASCII2,
        "border_style": session.options.get("rich_border_style"),
        "header_style": session.options.get("rich_header_style"),
        "title_style": session.options.get("rich_header_style"),
        "expand": True,
    }

    title = data.get("title", None)
    if title:
        kwargs["title"] = title

    if session.uses_screenreader():
        kwargs["box"] = None

    t = Table(**kwargs)

    for column in data.get("columns", list()):
        kw = column.get("kwargs", dict())
        t.add_column(**kw)

    for row in data.get("rows", list()):
        t.add_row(*row)

    return "ansi", session.print(t), options


def markdown(session, data, options):
    md = Markdown(data)
    return "ansi", session.print(md), options


def text(session, data, options):
    if options.get("type", None) == "py_output":
        return "ansi", session.console.render_str(
            data,
            markup=False,
            highlight=True,
            highlighter=ReprHighlighter(),
        ), options
    return "text", data, options


def traceback(session, data, options):
    tb = AthanorTraceback(show_locals=True)
    tb.box = ASCII2
    return "ansi", session.print(tb), options


def rich(session, data, options):
    return "ansi", session.print(data), options
