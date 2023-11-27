class Table:
    class Column:
        def __init__(self, table, header=None, col_type="str", **kwargs):
            self.table = table
            self.index = len(table.columns)
            self.col_type = col_type
            self.kwargs = kwargs
            if header is not None:
                kwargs["header"] = header

        def render(self, caller, options):
            out = dict()
            out["col_type"] = self.col_type
            if self.kwargs:
                out["kwargs"] = self.kwargs
            return out

        def render_data(self, data):
            if callable(method := getattr(self, f"render_data_{self.col_type}", None)):
                return method(data)
            else:
                return str(data)

    class Row:
        def __init__(self, table, *args):
            self.table = table
            self.index = len(table.rows)
            self.args = args

        def render(self, caller, options):
            out = list()
            for i, arg in enumerate(self.args):
                column = self.table.columns[i]
                out.append(column.render_data(arg))
            return out

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

    def render(self, caller, options):
        out = dict()
        if self.title:
            out["title"] = self.title
        if self.kwargs:
            out["kwargs"] = self.kwargs
        out["rows"] = [r.render(caller, options) for r in self.rows]
        out["columns"] = [c.render(caller, options) for c in self.columns]
        return out
