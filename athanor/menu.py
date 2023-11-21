from evennia import CmdSet
from .commands import AthanorCommand


class AthanorMenuCommand(AthanorCommand):
    menu_sort = 0

    def at_post_cmd(self):
        return self.true_cmdset.at_post_cmd(self)

    @property
    def true_cmdset(self):
        cmdsets = {c.key: c for c in self.caller.cmdset.all()}
        return cmdsets.get("menu", None)


class CmdExit(AthanorMenuCommand):
    menu_sort = 9999999
    key = "exit"
    syntax = "exit"
    desc = "Exit the Menu"

    def func(self):
        self.true_cmdset.end_menu()


class CmdMenu(AthanorMenuCommand):
    menu_sort = 999999
    key = "menu"
    syntax = "menu"
    desc = "Display this help Menu"

    def func(self):
        self.caller.ndb.cmdset = self.true_cmdset
        self.true_cmdset.render_menu()


class MenuCmdSet(CmdSet):
    # generally should not be changed.
    key = "menu"
    # This will be used to set the help_category on all menu-commands.
    help_category = "Athanor Menu"
    command_classes = [CmdMenu, CmdExit]
    priority = 50
    account_caller = False

    def at_cmdset_creation(self):
        for cmd in self.command_classes:
            cmd.help_category = self.help_category
            cmd.account_caller = self.account_caller
            self.add(cmd)

    def at_post_cmd(self, cmd):
        pass

    def end_menu(self):
        self.cmdsetobj.cmdset.remove(self)
        self.cmdsetobj.msg(f"Leaving the {self.help_category}.")

    def render_menu(self):
        pass

    def get_commands(self):
        if hasattr(self, "commands_sorted"):
            return self.commands_sorted
        commands = self.commands.copy()
        commands.sort(key=lambda x: getattr(x, "menu_sort", 0))
        self.commands_sorted = commands
        return commands

    @property
    def msg(self):
        return self.cmdsetobj.msg
