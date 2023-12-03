from rich.table import Table as RichTable
from rich.box import ASCII2
from rich.markdown import Markdown as RichMarkdown
from rich.highlighter import ReprHighlighter

from evennia.server.sendables import Sendable

import athanor
from athanor.error import AthanorTraceback
from athanor.ansi import RavensGleaning
from bs4 import BeautifulSoup


class Table(Sendable):
    render_types = ("ansi", "html", "json")

    class Column:
        def __init__(self, table, header=None, col_type="str", **kwargs):
            self.table = table
            self.index = len(table.columns)
            self.col_type = col_type
            self.kwargs = kwargs
            if header is not None:
                kwargs["header"] = header

        def serialize(self):
            out = dict()
            out["col_type"] = self.col_type
            if self.kwargs:
                out["kwargs"] = self.kwargs
            return out

        def render_ansi(self, session, data) -> ():
            if callable(method := getattr(self, f"render_ansi_{self.col_type}", None)):
                return method(session, data)
            else:
                return str(data)

        def render_html(self, session, data):
            if callable(method := getattr(self, f"render_html_{self.col_type}", None)):
                return method(session, data)
            else:
                return str(data)

        def render_html_str(self, session, data):
            return RAVEN.convert(data)

        def render_json(self, session, data):
            if callable(method := getattr(self, f"render_json_{self.col_type}", None)):
                return method(session, data)
            else:
                return str(data)

        def render_json_number(self, session, data):
            return data

    class Row:
        def __init__(self, table, *args):
            self.table = table
            self.index = len(table.rows)
            self.args = args

        def serialize(self):
            return self.args

        def fill_args(self):
            if len(self.args) < len(self.table.columns):
                self.args += [""] * (len(self.table.columns) - len(self.args))

        def render_ansi(self, session, kwargs):
            self.fill_args()
            return [
                c.render_ansi(session, d) for c, d in zip(self.table.columns, self.args)
            ]

        def render_json(self, session, kwargs):
            self.fill_args()
            return [
                c.render_json(session, d) for c, d in zip(self.table.columns, self.args)
            ]

        def render_html(self, session, kwargs):
            self.fill_args()
            return [
                c.render_html(session, d) for c, d in zip(self.table.columns, self.args)
            ]

    def __init__(self, title=None, **kwargs):
        self.title = title
        self.rows = list()
        self.columns = list()
        self.kwargs = kwargs

    def add_row(self, *args):
        self.rows.append(self.Row(self, *args))

    def add_column(self, header=None, col_type="str", **kwargs):
        self.columns.append(
            self.Column(self, header=header, col_type=col_type, **kwargs)
        )

    def serialize(self):
        out = dict()
        if self.title:
            out["title"] = self.title
        if self.kwargs:
            out["kwargs"] = self.kwargs
        out["rows"] = [r.serialize() for r in self.rows]
        out["columns"] = [c.serialize() for c in self.columns]
        return out

    @classmethod
    def deserialize(cls, data):
        out = cls(title=data.get("title", None), **data.get("kwargs", dict()))
        for col in data.get("columns", list()):
            out.add_column(**col)
        for row in data.get("rows", list()):
            out.add_row(*row)
        return out

    def render_html(self, session, kwargs) -> str:
        soup = BeautifulSoup("", "html.parser")
        table = soup.new_tag("table")
        # still working on this obviously...

    def render_json(self, session, kwargs) -> (str, list, dict):
        return self.serialize()

    def render_ansi(self, session, kwargs) -> str:
        table_kwargs = {
            "box": ASCII2,
            "border_style": session.options.get("rich_border_style"),
            "header_style": session.options.get("rich_header_style"),
            "title_style": session.options.get("rich_header_style"),
            "expand": True,
        }

        if self.title:
            table_kwargs["title"] = self.title

        if session.uses_screenreader():
            table_kwargs["box"] = None

        t = RichTable(**table_kwargs)

        for column in self.columns:
            t.add_column(**column.kwargs)

        for row in self.rows:
            t.add_row(*row.render_ansi(session, kwargs))

        return session.print(t)


class Representation(Sendable):
    def __init__(self, text, **kwargs):
        self.text = text

    def serialize(self):
        return self.text

    @classmethod
    def deserialize(cls, data):
        return cls(data)

    def render_html(self, session, kwargs) -> str:
        pass

    def render_json(self, session, kwargs) -> (str, list, dict):
        return ("representation", self.text)

    def render_ansi(self, session, kwargs) -> str:
        rendered = session.console.render_str(
            self.text, markup=False, highlight=True, highlighter=ReprHighlighter()
        )
        return session.print(rendered)


class Text(Sendable):
    render_types = ("ansi", "html", "json")

    @classmethod
    def from_msg(cls, data, **kwargs):
        if kwargs.get("type", None) == "py_output":
            r = athanor.SENDABLES.get("representation")
            return r(data, **kwargs)
        return cls(data, **kwargs)

    def __init__(self, text: str | ANSIString, **kwargs):
        self.text = text if isinstance(text, ANSIString) else ANSIString(text)

    def serialize(self):
        return str(self.text)

    @classmethod
    def deserialize(cls, data):
        return cls(data)

    def render_html(self, session, kwargs) -> str:
        return RAVEN.convert(str(self.text))

    def render_json(self, session, kwargs) -> str:
        return str(self.text)

    def render_ansi(self, session, kwargs) -> str:
        return str(self.text)


class Markdown(Sendable):
    render_types = ("ansi", "html", "json")

    @classmethod
    def from_msg(cls, data, **kwargs):
        return cls(data, **kwargs)

    def __init__(self, text: str, **kwargs):
        self.text = text

    def serialize(self):
        return self.text

    @classmethod
    def deserialize(cls, data):
        return cls(data)

    def render_html(self, session, kwargs) -> str:
        pass

    def render_json(self, session, kwargs) -> str:
        return ("markdown", str(self.text))

    def render_ansi(self, session, kwargs) -> str:
        md = RichMarkdown(self.text)
        return session.print(md)
