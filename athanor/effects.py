import typing
import sys
from collections import defaultdict
from athanor import EFFECT_COMPONENTS, EFFECT_CLASSES


class EffectComponent:
    """
    A base class for all EffectComponents. An EffectComponent is an aspect of a grander Effect. For instance,
    a status modifier which represents being doused in flammable oil might have two EffectComponents:

    One which triggers an OnFire Effect when the character is hit with a fire attack, and the other
    a stat penalty to dexterity to represent being all slippery. These might be a class called
    NewEffectOnElementDamageComponent, and another called StatDebuffComponent

    EffectComponent classes are loaded at startup from settings.EFFECT_COMPONENT_PATHS into athanor.EFFECT_COMPONENTS.

    A subclass of EffectComponent is meant to be instantiated from pure data, like JSON or a python dictionary, to
    set its properties. So, the way it's meant to be used, then, is to create subclasses of EffectComponent which
    Do Stuff(TM) and then create systems which can generate or retrieve that data from files or from randomized
    templates, whatever.

    An Effect MIGHT contain multiple EffectComponents of the same type/class. For instance, a character might have
    two different DamageOverTimeComponents on the same effect active at the same time. This is why EffectComponents
    are stored in a list on the Effect, but are also indexed by their type.

    EffectComponents are serialized as a list of key-value pairs in the Effect's attributes.

    The key is the name of the subclass, by default, but this can be overridden using the @classmethod get_name().
    Be careful with this either way, as subclasses loaded later in the game will replace those loaded earlier
    in athanor.EFFECT_COMPONENTS

    When designing components, it is recommended that they contain all the logic needed to do their thing.
    For instance, a DamageOverTimeComponent might operate on a range of damage numbers like [1-5], or [1-5]%
    If these values can be repeatedly reproduced from something like an Item, then the entire Effect won't need
    to be Persistent. It also means that the Effect will be refreshed if the item's prototype changes.
    """
    # The attributes which should be saved to the attribute-dict for this effectcomponent, if the Effect is persistent.
    persistent_attrs = ["tags"]

    def __init__(self, effect, tags: typing.Tuple[str] = None, **kwargs):
        """
        Creates an EffectComponent.

        Args:
            effect (Effect): The Effect this component is attached to.
            tags (tuple of str): A list of tags to apply to this component. These are used to identify the component
        """
        if tags is None:
            tags = tuple()

        # The Effect this component is attached to.
        self.effect = effect

        # The handler this component is attached to.
        self.handler = effect.handler

        # The object this affect ultimately applies to.
        self.owner = effect.handler.owner

        self.tags = tags

    def is_enabled(self) -> bool:
        return True

    def generate_description(self) -> str:
        return ""

    @classmethod
    def get_name(cls):
        return getattr(cls, "name", cls.__name__)

    def export(self) -> typing.Tuple[str, dict]:
        """
        Exports this EffectComponent as a key-value pair.
        """
        out = dict()
        for attr in self.persistent_attrs:
            out[attr] = getattr(self, attr)
        return self.get_name(), out


class Effect:
    """
    An Effect is a collection of EffectComponents which are applied to a target. For instance, a status modifier, a
    transformation, a magical enchantment, or even the benefits of an equipped item.

    An Effect shouldn't really "do" anything itself; it is merely a container for EffectComponents, serving to
    organize them and provide a common interface for them to interact with each other and the world.

    An Effect's components should be set when it's created, and not later changed. Rather than changing individual
    effects, it is better to implement a mechanism to determine whether they're currently enabled or not.

    As with EffectComponents, Effects are loaded at startup from settings.EFFECT_PATHS into athanor.EFFECT_CLASSES.
    The Effect class can be subclassed to provide additional functionality, but it's not necessary.

    It is recommended to be careful with persistent effects, as they can lead to breaks in code if the classes they
    want to load stop existing. It's better to use a non-persistent effects which are applied when the character loads
    or equips/unequips items and so on, and be careful with persistent effects. Non-persistent effects are kept only
    in RAM, which means they're easily regenerated from templates and so on, and they're also easily refreshed if
    their source material changes.
    """
    # The attributes which should be saved to the attribute-dict for this Effect, if it's Persistent.
    persistent_attrs = ["tags", "description", "source"]

    def __init__(self, handler, name: typing.Union[str, "AthanorItem"], source=None,
                 description: typing.Optional[str] = None, persistent: bool = False, **kwargs):
        """
        Creates an Effect.

        Args:
            handler: The handler this Effect is attached to.
            name (str or AthanorItem): The name of this Effect. This is used to identify the Effect in the
                handler's dictionary of Effects. It might be a direct reference to an ObjectDB, or it might be
                a string. An ObjectDB reference is meant to handle Effects attached to equipped Items.

        """
        self.handler = handler
        self.owner = handler.owner
        self.name = name
        self.source = source
        self.components = list()
        self.persistent = persistent

        # An index of the components by their type. This allows for easy iteration through 'all StatDebuffComponents'
        # as an example.
        self.components_type_map = defaultdict(set)

        # The tag map is similar to the type map in that it organizes components by their tags. This allows for
        # even easier iteration through components using a scheme. For instance, StatBuffComponent
        # and StatDebuffComponent might use the "stat" tag so that they can be iterated as a group.
        # Alternatively, they might have a stat_strength tag for even clearer organization - it's now easy
        # to grab all stats which numerically affect stat_strength.

        self.components_tag_map = defaultdict(set)
        self.description = sys.intern(description) if description else None

    def load(self, component_data: list):
        """
        Instantiates/loads the EffectComponents from a list of key-value pairs.
        It's a list, because the same EffectComponent class might be used multiple times.
        """
        for key, data in component_data:
            component_class = EFFECT_COMPONENTS.get(key, None)
            if not component_class:
                continue  # TODO: this should probably error somehow... but how to do so usefully?
            try:
                component = component_class(self, **data)
                self.components.append(component)
                self.components_type_map[key].add(component)
                for tag in component.tags:
                    self.components_tag_map[tag].add(component)
            except Exception as err:
                pass  # TODO: this should probably error somehow... but how to do so gracefully?

    def get_name(self, looker=None) -> str:
        if isinstance(self.name, str):
            return self.name
        if not looker:
            looker = self.owner
        if hasattr(self.name, "get_display_name"):
            return self.name.get_display_name(looker=looker)
        return "Unknown Effect!"

    def generate_description(self) -> str:
        """
        Generates a useful description of this Effect for player consumption so they know what is,
        where it came from, what it does, etc.
        """
        return self.description or ""

    @classmethod
    def get_class_name(cls) -> str:
        return getattr(cls, "class_name", cls.__name__)

    def export(self) -> typing.Tuple[str, dict]:
        """
        Exports this Effect for serialization by the EffectHandler.
        """
        out = dict()
        for attr in self.persistent_attrs:
            out[attr] = getattr(self, attr)
        out["component_data"] = [component.export() for component in self.components]
        out["effect_class"] = self.get_class_name()

        return self.name, out


class EffectHandler:
    """
    The EffectHandler which is attached to an ObjectDB to handle all of its Effects.
    """
    attr_save = "effects"
    base_effect_class = Effect

    def __init__(self, owner):
        self.owner = owner

        # Effects are indexed by their effect.name, which is either a string or an ObjectDB reference.
        self.effects = dict()
        self.component_tags = defaultdict(set)
        self.component_types = defaultdict(set)

        self.load()

    def add_effect(self, name: typing.Union[str, "AthanorItem"], effect_class: typing.Union[str, typing.Type[Effect]] = None, source=None,
                   component_data: list = None, description: str = None, persistent: bool = False, **kwargs):
        """
        A reminder: All Effects MUST have a unique name. There's no practical way to check for that here, so it's
        on the developers.
        """
        if isinstance(effect_class, str):
            effect_class = EFFECT_CLASSES.get(effect_class, self.base_effect_class)
        if not effect_class:
            return  # TODO: This should error somehow...
        effect = effect_class(self, name=name, source=source, description=description, persistent=persistent, **kwargs)
        if component_data:
            effect.load(component_data)
        self.effects[name] = effect
        for comp_type in effect.components_type_map:
            self.component_types[comp_type] += effect.components_type_map[comp_type]
        for tag in effect.components_tag_map:
            self.component_tags[tag] += effect.components_tag_map[tag]
        if persistent:
            self.save()

    def remove_effect(self, name: typing.Union[str, "AthanorItem"]):
        if eff := self.effects.get(name, None):
            for comp_type in eff.components_type_map:
                self.component_types[comp_type] -= eff.components_type_map[comp_type]
            for tag in eff.components_tag_map:
                self.component_tags[tag] -= eff.components_tag_map[tag]
            del self.effects[name]
            if eff.persistent:
                self.save()

    def save(self):
        """
        Saves the EffectHandler's Persistent Effects to the owner's attributes.
        """
        out_data = list()
        for key, effect in self.effects.items():
            if not effect.persistent:
                continue
            out_data.append(effect.export())
        self.owner.attributes.add(key=self.attr_save, value=out_data)

    def load(self):
        """
        Loads up all Effects that this EffectHandler is supposed to have.
        """
        # First, we load the persistent effects.
        self.load_from_attribute()
        # Since we don't know exactly where all of the Effects are coming from, we will ask the owner class
        # to initialize any Effects it wants to have.
        self.owner.init_effects()

    def load_from_attribute(self):
        """
        Loads the EffectHandler's Persistent Effects from the owner's attributes.
        """
        for name, data in self.owner.attributes.get(self.attr_save, list()):
            self.add_effect(name=name, persistent=True, **data)
