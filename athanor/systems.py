from athanor import PENDING_COMMANDS
import asyncio
from datetime import datetime
from django.conf import settings


class System:
    name = "system"
    interval = 0.0

    def __init__(self):
        self.task = None

    def at_init(self):
        pass

    def at_start(self):
        pass

    async def update(self):
        pass

    def at_stop(self):
        pass

    def at_reload_start(self):
        pass

    def at_reload_stop(self):
        pass

    def at_cold_start(self):
        pass

    def at_cold_stop(self):
        pass


class CmdQueueSystem(System):
    name = "cmdqueue"
    interval = 0.1

    async def update(self):
        # First, copy the current pending commands and clear them.
        # this allows for new additions to PENDING_COMMANDS be made during iteration.
        pending = set(PENDING_COMMANDS)
        PENDING_COMMANDS.clear()

        for obj in pending:
            if obj.cmdqueue.check(self.interval):
                # put any objects with commands still pending back into the queue.
                PENDING_COMMANDS.add(obj)
            await asyncio.sleep(0)


class PlaySystem(System):
    name = "play"
    interval = 1.0

    def __init__(self):
        super().__init__()
        from athanor.plays.plays import DefaultPlay
        self.play = DefaultPlay

    async def update(self):
        for play in self.play.objects.all():
            play.last_good = datetime.utcnow()
            if not play.sessions.count():
                play.timeout_seconds = play.timeout_seconds + self.interval
                if play.timeout_seconds >= settings.PLAY_TIMEOUT_SECONDS:
                    play.at_timeout()

    def at_cold_start(self):
        for play in self.play.objects.all():
            play.at_server_cold_start()

    def at_cold_stop(self):
        for play in self.play.objects.all():
            play.at_server_cold_stop()