from evennia.commands.command import Command as BaseCommand
from evennia.commands.default.muxcommand import MuxCommand as MuxCmd, MuxAccountCommand as MuxAccCmd


class Command(BaseCommand):
    pass


class AccountCommand(Command):
    account_caller = True


class MuxCommand(MuxCmd):
    pass


class MuxAccountCommand(MuxAccCmd):
    pass
