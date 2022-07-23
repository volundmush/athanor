class EquipSlot:
    key = None
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


class _Finger(EquipSlot):
    slot_type = "finger"


class RightRingFinger(_Finger):
    key = "right_ring_finger"
    wear_display = "on $pron(your) right ring finger"
    list_display = "On Right Ring Finger"
    remove_display = "from $pron(your) right ring finger"
    sort_order = 10


class LeftRingFinger(_Finger):
    key = "left_ring_finger"
    wear_display = "on $pron(your) left ring finger"
    list_display = "On Left Ring Finger"
    remove_display = "from $pron(your) left ring finger"
    sort_order = 20


class Neck1(EquipSlot):
    key = "neck_1"
    wear_display = "around $pron(your) neck"
    remove_display = "from $pron(your) neck"
    slot_type = "neck"
    list_display = "Worn Around Neck"
    sort_order = 30


class Neck2(Neck1):
    key = "neck_2"
    slot_type = "neck"
    list_display = "Worn Around Neck"
    sort_order = 35


class Body(EquipSlot):
    key = "body"
    wear_display = "around $pron(your) body"
    remove_display = "from $pron(your) body"
    slot_type = "body"
    list_display = "Worn On Body"
    sort_order = 40


class Head(EquipSlot):
    key = "head"
    wear_display = "on $pron(your) head"
    remove_display = "from $pron(your) head"
    slot_type = "head"
    list_display = "Worn On Head"
    sort_order = 50


class Legs(EquipSlot):
    key = "legs"
    wear_display = "on $pron(your) legs"
    remove_display = "from $pron(your) legs"
    slot_type = "legs"
    list_display = "Worn On Legs"
    sort_order = 60


class Feet(EquipSlot):
    key = "feet"
    wear_display = "on $pron(your) feet"
    remove_display = "from $pron(your) feet"
    slot_type = "feet"
    list_display = "Worn On Feet"
    sort_order = 70


class Hands(EquipSlot):
    key = "hands"
    wear_display = "on $pron(your) hands"
    remove_display = "from $pron(your) hands"
    slot_type = "hands"
    list_display = "Worn On Hands"
    sort_order = 80


class Arms(EquipSlot):
    key = "arms"
    wear_display = "on $pron(your) arms"
    remove_display = "from $pron(your) arms"
    slot_type = "arms"
    list_display = "Worn On Arms"
    sort_order = 90


class About(EquipSlot):
    key = "about"
    wear_display = "about $pron(your) body"
    remove_display = "from about $pron(your) body"
    slot_type = "about"
    list_display = "Worn About Body"
    sort_order = 100


class Waist(EquipSlot):
    key = "waist"
    wear_display = "around $pron(your) waist"
    remove_display = "from $pron(your) waist"
    slot_type = "waist"
    list_display = "Worn About Waist"
    sort_order = 110


class RightWrist(EquipSlot):
    key = "right_wrist"
    wear_display = "around $pron(your) right wrist"
    remove_display = "from $pron(your) right wrist"
    slot_type = "wrist"
    list_display = "Worn On Right Wrist"
    sort_order = 120


class LeftWrist(EquipSlot):
    key = "left_wrist"
    wear_display = "around $pron(your) left wrist"
    remove_display = "from $pron(your) left wrist"
    slot_type = "wrist"
    list_display = "Worn On Left Wrist"
    sort_order = 125


class Wield1(EquipSlot):
    key = "wield_1"
    wear_verb = "$conj(wields)"
    wear_display = "as $pron(your) primary weapon"
    remove_verb = "$conj(stops) using"
    remove_display = "as $pron(your) primary weapon"
    slot_type = "wield"
    list_display = "Wielded"
    sort_order = 130


class Wield2(EquipSlot):
    key = "wield_2"
    wear_verb = "$conj(holds)"
    wear_display = "in $pron(your) offhand"
    remove_verb = "$conj(stops) holding"
    remove_display = "in $pron(your) offhand"
    slot_type = "wield"
    list_display = "Offhand"
    sort_order = 135


class Back(EquipSlot):
    key = "back"
    wear_display = "on $pron(your) back"
    remove_display = "from $pron(your) back"
    slot_type = "back"
    list_display = "Worn on Back"
    sort_order = 140


class RightEar(EquipSlot):
    key = "right_ear"
    wear_display = "on $pron(your) right ear"
    remove_display = "from pron(your) right ear"
    slot_type = "ear"
    list_display = "Worn on Right Ear"
    sort_order = 150


class LeftEar(EquipSlot):
    key = "left_ear"
    wear_display = "on $pron(your) left ear"
    remove_display = "from $pron(your) left ear"
    slot_type = "ear"
    list_display = "Worn on Left Ear"
    sort_order = 155


class Shoulders(EquipSlot):
    key = "shoulders"
    wear_display = "on $pron(your) shoulders"
    remove_display = "from $pron(your) shoulders"
    slot_type = "shoulders"
    list_display = "Worn on Shoulders"
    sort_order = 160


class Eyes(EquipSlot):
    key = "eyes"
    wear_display = "over $pron(your) eyes"
    remove_display = "from $pron(your) eyes"
    slot_type = "eyes"
    list_display = "Worn Over Eyes"
    sort_order = 170
