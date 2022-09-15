class EquipSlot:
    key = None
    category = None
    slot_type = None
    sort_order = 0
    wear_verb = "$conj(wears)"
    wear_display = "on $pron(your) body"
    remove_verb = "$conj(removes)"
    remove_display = "from $pron(your) body"

    def __init__(self, handler, item):
        self.handler = handler
        self.item = item

    def display_slot(self):
        if hasattr(self, "list_display"):
            return self.list_display
        return self.__class__.__name__

    def display_contents(self, looker, **kwargs):
        return self.item.get_display_name(looker=looker, **kwargs)


    @classmethod
    def is_available(cls, equipper, **kwargs):
        return True
