import random

# Import the base class with an underscore so as not to mess with classes_from_modules.
from .effects import EffectComponent as _EffectComponent


class ModifierStatic(_EffectComponent):
    """
    A basic EffectComponent which simply adds a static value to the target's modifier when added/enabled,
    and removes it when disabled/removed.
    """

    __slots__ = ("modifier", "value")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.modifier = kwargs.get("modifier", None)
        self.value = kwargs.get("value", 0.0)

    def on_disable(self):
        modifier = self.handler.get_modifier(self.modifier)
        modifier.modify(-self.value)

    def on_enable(self):
        modifier = self.handler.get_modifier(self.modifier)
        modifier.modify(self.value)


class ModifierRandom(_EffectComponent):
    """
    This Modifier applies a randomized value to the target's modifier when it's calculated.
    """

    __slots__ = ("modifier", "min", "max")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.modifier = kwargs.get("modifier", None)
        self.min = kwargs.get("min", 0.0)
        self.max = kwargs.get("max", 0.0)

    def on_calculate(self):
        return random.uniform(self.min, self.max)

    def on_disable(self):
        modifier = self.handler.get_modifier(self.modifier)
        modifier.dynamic.remove(self)

    def on_enable(self):
        modifier = self.handler.get_modifier(self.modifier)
        modifier.dynamic.add(self)


class ModifierDynamic(_EffectComponent):
    """
    This modifier applies a dynamic value to the target's modifier when it's calculated.

    The base version of this component directs on_calculate() to call self.effect.calculate_dynamic(), which needs to be
    implemented on special Effects. It is probably much more useful to subclass this and override on_calculate() to
    not need to do that.
    """

    __slots__ = ("modifier",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.modifier = kwargs.get("modifier", None)

    def on_calculate(self):
        return self.effect.calculate_dynamic(self.modifier)

    def on_disable(self):
        modifier = self.handler.get_modifier(self.modifier)
        modifier.dynamic.remove(self)

    def on_enable(self):
        modifier = self.handler.get_modifier(self.modifier)
        modifier.dynamic.add(self)
