from athanor.utils import utcnow
from athanor import CHARACTERS_ONLINE


def playtime(*args, **kwargs):
    n = utcnow()
    for char in CHARACTERS_ONLINE:
        char.db.last_online = n
