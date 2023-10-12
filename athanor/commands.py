from evennia.commands.default.muxcommand import MuxCommand, MuxAccountCommand


class _AthanorCommandMixin:
    pass


class AthanorCommand(_AthanorCommandMixin, MuxCommand):
    """
    This is a base command for all Athanor commands.
    """
    pass


class AthanorAccountCommand(_AthanorCommandMixin, MuxAccountCommand):
    """
    This is a base command for all Athanor commands.
    """
    pass
