from athanor import PENDING_COMMANDS
from athanor.dgscripts.models import DGScriptDB, DGInstanceDB
from evennia.objects.models import ObjectDB
from datetime import datetime
from django.conf import settings
from athanor.utils import utcnow
from athanor.dgscripts.dgscripts import DGState
from django.db.models import F, Q
from twisted.internet import reactor, task

def sleep_for(delay):
    return task.deferLater(reactor, delay, lambda: None)


class System:
    name = "system"
    interval = 0.0

    def __init__(self):
        self.looper = None
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
            await sleep(0)


class PlaySystem(System):
    name = "play"
    interval = 1.0

    def __init__(self):
        super().__init__()
        from athanor.plays.plays import DefaultPlay
        self.play = DefaultPlay

    async def update(self):
        for play in self.play.objects.all():
            play.last_good = utcnow()
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


class DGWaitSystem(System):
    name = "dgwait"
    interval = 0.5

    async def update(self):
        obj_ids = set(DGInstanceDB.objects.filter(db_state=int(DGState.WAITING)).values_list("db_holder", flat=True))

        for i in obj_ids:
            if not (obj := ObjectDB.objects.filter(id=i).first()):
                continue
            obj.dgscripts.resume()
            await sleep_for(0)


class DGResetSystem(System):
    name = "dgreset"
    interval = 1.0

    async def update(self):
        obj_ids = set(DGInstanceDB.objects.filter(db_state__gt=2).values_list("db_holder", flat=True))

        for i in obj_ids:
            if not (obj := ObjectDB.objects.filter(id=i).first()):
                continue
            obj.dgscripts.reset_finished()
            await sleep_for(0)


class DGRandomSystem(System):
    name = "dgrandom"
    interval = 13.0

    async def update(self):
        obj_ids = set(DGInstanceDB.objects.filter(Q(db_state=0) & F('db_script_db_trigger_type').bitand(2)).values_list("db_holder", flat=True))

        for i in obj_ids:
            if not (obj := ObjectDB.objects.filter(id=i).first()):
                continue
            obj.dgscripts.trigger_random()
            await sleep_for(0)
