from athanor.utils import utcnow
from athanor.typeclasses.characters import AthanorPlayerCharacter


def playtime(*args, **kwargs):
    n = utcnow()
    for char in AthanorPlayerCharacter.objects.get_by_tag(key="puppeted", category="account"):
        char.db.last_online = n
