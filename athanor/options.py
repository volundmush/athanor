"""
Contains additional OptionClasses for Athanor.
"""
from evennia.utils.optionclasses import BaseOption
from rich.style import Style as _RichStyle
from rich.errors import StyleSyntaxError


class Style(BaseOption):
    """
    Class which handles Rich Style storage for OptionHandlers.
    """

    def validate(self, value, **kwargs):
        try:
            style = _RichStyle.parse(value)
        except StyleSyntaxError as err:
            return ValueError(f"Invalid Rich style: {err}")
        return style

    def default(self):
        return _RichStyle.parse(self.default_value)

    def deserialize(self, save_data):
        return _RichStyle.parse(save_data)

    def serialize(self):
        return str(self.value_storage)

    def display(self, **kwargs):
        return str(self.value)
