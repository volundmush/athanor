from .base import Command
from athanor import PENDING_COMMANDS

class ClearQueue(Command):
    key = "--"

    def func(self):
        match self.caller.cmdqueue.clear():
            case True:
                self.msg("Your command queue is cleared!")
            case False:
                self.msg("There are no commands to clear from your queue!")


class CmdQueueHandler:

    def __init__(self, owner):
        self.owner = owner
        self.queue = list()
        self.wait_time = 0.0

    def add(self, cmd):
        self.queue.append(cmd)
        PENDING_COMMANDS.add(self.owner)

    def clear(self):
        if self.queue:
            self.queue.clear()
            return True
        return False

    def execute(self):
        if self.queue:
            try:
                cmd = self.queue.pop(0)
                cmd.parse()
                if not cmd.can_perform_command():
                    return
                cmd.func()
                cmd.at_post_cmd()
            except Exception as err:
                self.owner.msg(err)

    def check(self, decrement: float) -> bool:
        self.wait_time = max(0.0, self.wait_time - decrement)
        if self.wait_time <= 0:
            self.execute()
        return bool(self.queue)

    def set_wait(self, wait_time: float = 0.0):
        self.wait_time = wait_time


class QueueCommand(Command):
    """
    This class of command exploits at_pre_cmd to avoid firing instantly. Instead,
    it's added to a queue which is called periodically by a service.

    The QueueHandler must be lazy-property'd to the caller as cmdqueue for this to
    work.
    """

    def at_pre_cmd(self):
        """
        Prevent normal execution and enqueue instead.
        """
        self.caller.cmdqueue.add(self)
        return True

    def can_perform_command(self):
        """
        Used in place of at_pre_cmd by the queue system.
        """
        return True

    def func(self):
        self.msg("Sorry, this command hasn't been implemented yet.")
