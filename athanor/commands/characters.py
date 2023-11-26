from .base import AthanorCommand


class CmdOSay(AthanorCommand):
    """
    Speak out of character.

    Usage:
        osay <message>
    """

    key = "osay"
    locks = "cmd:all()"
    help_category = "Comms"

    def func(self):
        if not self.args:
            self.msg("Say what? (Usage: osay <message>)")
            return

        if not self.caller.location:
            self.msg("You have no location.")
            return

        message = self.args.strip()
        final_message = "|w-<|rOOC|w>-|n $You()"
        if message.startswith(":"):
            final_message += f" {message[1:]}"
        elif message.startswith(";"):
            final_message += f"{message[1:]}"
        else:
            final_message += f' $conj(say), "{message}"'
        self.caller.location.msg_contents(final_message, from_obj=self.caller)
