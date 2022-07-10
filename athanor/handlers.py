
class InventoryHandler:
    attr_name = "inventory"

    def __init__(self, owner):
        self.owner = owner
        self.data = None
        self.load()

    def load(self):
        if not self.owner.attributes.has(self.attr_name):
            self.owner.attributes.add(self.attr_name, list())
        self.data = self.owner.attributes.get(self.attr_name)

    def all(self):
        return list(self.data)

    def add(self, obj):
        self.data.append(obj)

    def remove(self, obj):
        if obj in self.data:
            self.data.remove(obj)

    def dump(self):
        contents = self.all()
        self.data.clear()
        return contents


class EquipmentHandler:
    attr_name = "equipment"
    reverse_name = "equipped"

    def __init__(self, owner):
        self.owner = owner
        self.data = None
        self.load()

    def load(self):
        if not self.owner.attributes.has(self.attr_name):
            self.owner.attributes.add(self.attr_name, dict())
        self.data = self.owner.attributes.get(self.attr_name)

    def all(self):
        return list(self.data.values())

    def get(self, slot: int):
        return self.data.get(slot, None)

    def equip(self, slot: int, obj):
        self.data[slot] = obj
        obj.location = self.owner
        obj.attributes.add(self.reverse_name, (slot, self.owner))

    def remove(self, slot: int):
        found = self.data.pop(slot, None)
        if found:
            found.attributes.remove(self.reverse_name)
        return found


class WeightHandler:
    attr_name = "weight"

    def __init__(self, owner):
        self.owner = owner
        self.data = None
        self.load()

    def load(self):
        if not self.owner.attributes.has(self.attr_name):
            self.owner.attributes.add(self.attr_name, 0.0)
        self.data = self.owner.attributes.get(self.attr_name)

    def set(self, value: float):
        self.data = value
        self.save()

    def get_bonuses(self) -> (int, float):
        bonus = 0
        mult = 1.0
        for m in self.owner.get_all_modifiers():
            bonus += m.stat_bonus(self.owner, self.attr_name)
            mult += m.stat_multiplier(self.owner, self.attr_name)
        return (bonus, mult)

    def personal(self):
        bonus, mult = self.get_bonuses()
        return (self.data + bonus) * mult

    def get(self) -> float:
        return self.data

    def save(self):
        self.owner.attributes.add(self.attr_name, self.data)

    def total(self) -> float:
        return self.personal() + self.burden()

    def burden(self) -> float:
        return self.equipped() + self.carried()

    def equipped(self) -> float:
        out = 0.0
        if hasattr(self.owner, "equipment") and not self.owner.ignore_equipped_weight():
            for o in self.owner.equipment.all():
                out += o.weight.total()
        return out

    def carried(self) -> float:
        out = 0.0
        if hasattr(self.owner, "inventory") and not self.owner.ignore_carried_weight():
            for o in self.owner.inventory.all():
                out += o.weight.total()
        return out