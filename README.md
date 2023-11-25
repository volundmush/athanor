# Athanor - Alchemical Wizardry for Evennia

## WARNING:  Alpha!
Pardon our dust, this project is heavily WIP. It runs, but is unstable and subject to substantial changes.

## CONTACT INFO
**Name:** Volund

**Email:** volundmush@gmail.com

**PayPal:** volundmush@gmail.com

**Discord:** VolundMush  

**Discord Channel:** https://discord.gg/Sxuz3QNU8U

**Patreon:** https://www.patreon.com/volund

**Home Repository:** https://github.com/volundmush/athanor

## TERMS AND CONDITIONS

MIT license. In short: go nuts, but give credit where credit is due.

Please see the included LICENSE.txt for the legalese.

## INTRO
MUDs and their brethren are the precursors to our modern MMORPGs, and are still a blast to play - in addition to their other uses, such as educative game design: all the game logic, none of the graphics!

Evennia does a splendid job at providing the barebones basics of getting a MUD-like server up and running quickly, but in my opinion, it is lacking certain amenities, features, and niceties which many games will all want to have.

Thus, Athanor is here to provide a higher-level SDK atop of Evennia, where new features can be written as plugins and easily added to any existing project using Athanor.

The majority of my vision is based on experience from working with RPI MUDs and roleplay-themepark MUSHes and so much of the code will be built with those in mind.

## FEATURES
  * Plugin Framework with composable settings...
  * ... and many starting plugins!
  * Amazing ANSI and other Text Formatting powered by [Rich](https://github.com/willmcgugan/rich)
  * Easy installation.
  * Event Emitter
  * Utility functions.
  * Composable CmdSets
  * Extended Options/Style System.
  * Heavily extended/modified Evennia Lock system.
  * Login tracking that keeps track of who's logging in from where, when.
  * Playtime tracking - track how long accounts and characters are online. Even tracks characters-per-account for if characters change hands.

## OFFICIAL PLUGINS
  * A Myrrdin-style [BBS](https://github.com/volundmush/athanor_boards) with Board Collections and prefixes to organize boards for IC and OOC purposes. Similar to Forums, but with a classic MUX/MUSH feel.
  * Django-wiki integration via [Wiki](https://github.com/volundmush/athanor_wiki), for a wiki system. Many games use Wikis to list information about game setting, rules, and etc.
  * Django-helpdesk integration via [Helpdesk](https://github.com/volundmush/athanor_helpdesk) for an Issue Tracker and Knowledgebase.
  * Tabletop game packages such as [Storyteller](https://github.com/volundmush/storyteller) (WoD, Exalted, etc). This plugin is actually a family of plugins for supporting different games.
  * A [Faction System](https://github.com/volundmush/athanor_factions) for organizing guilds, organizations, and other such groups. Well-integrated with the lock system for Faction membership checks. Factions may be hierarchial, with sub-factions.
  * A [Zone System](https://github.com/volundmush/athanor_zones) for organizing Rooms, Exits, and other Objects into Zones. Zones themselves can be arranged in a tree-like hierarchy.
  * The [Roleplay System](https://github.com/volundmush/athanor_roleplay) provides scheduling and logging tools for roleplay sessions. (COMING SOON)
  * The [Backscroll System](https://github.com/volundmush/athanor_backscroll) records a configurable amount of text backscroll for each character, allowing players to catch up on missed activity.


## OKAY, BUT HOW DO I USE IT?
Glad you asked!

First, you'll need to install Evennia and create a game folder for your specific game. You can find instructions for that [here](https://www.evennia.com/docs/latest/Setup/Installation.html)

Then, you can install athanor using ```pip install git+git://github.com/volundmush/athanor```

Once it's installed, you will need to modify your settings.py to include the following section:

```python
import athanor as _athanor, sys as _sys
_athanor.init(_sys.modules[__name__], plugins=[

])
```
Notice the empty list. that should contain a list of strings naming Python modules which are compatible as plugins.
for instance,

```python
import athanor as _athanor, sys as _sys
_athanor.init(_sys.modules[__name__], plugins=[
    "athanor_boards",
    "athanor_wiki",
    "athanor_helpdesk",
])
```

The section should be directly below `from evennia.settings_default import *` and precede all other settings entries. This way, anything defined in plugins can be overriden further down in settings.py.

## OKAAAAAAY, SO HOW DO I -REALLY- USE IT?
The true power of Athanor is in making plugins. Athanor on its own doesn't do too much. But here are some of the things to keep in mind.

### PLUGINS
A plugin is a Python module which is accessible on your Python path. The module must define an `init(settings, plugins: dict)` method which will be called during Athanor startup. Check out athanor's own `__init__.py` to see how it's called.

### SETTINGS
This `init()` method will be passed a reference to the settings module, and a dictionary of plugins which are being loaded. Evennia's settings can be adjusted using `settings.BLAH = Whatever`. Be careful not to import anything which would bork `django.setup()` - it's best to work with simple data primitives.

Be careful to APPEND/EXTEND/INSERT INTO existing lists rather than outright replacing them, such as INSTALLED_APPS.

### DATABASE
Some Athanor Plugins may modify INSTALLED_APPS and require you to run `evennia migrate`

### COMMANDS
Athanor provides an AthanorCommand class subclassed from MuxCommand, which adds a bunch of new features such as auto-styled Rich tables and message dispatch convenience wrappers. Do check it out!

### CMDSETS
You know what I find annoying? Having to import a command module and then add all of its commands to a cmdset. Most of the time, the default cmdsets just need to have more commands piled onto them.

To make adding commands easier, Athanor's settings provide the `CMD_MODULES_<type>` lists, like `CMD_MODULES_ACCOUNT`.

Any Python modules added to this list will have their commands added to the respective default cmdsets by default.

NOTE: This is done via `evennia.utils.utils.callables_from_module`, which extracts all callables defined in a module (not imported) that do not begin with a _. These modules should NOT contain any other classes or functions, unless they begin with an underscore.

### LOCKS
Overall, Evennia's lock system is amazing. The concept of access_type and lockfuncs is great. However, encoding database IDs directly into strings is kind of a pain - imagine a game where characters are moved between accounts and having to constantly adjust the puppet lock, for instance? Or trying to bind an object's permissions to some kind of external access control list? How will you migrate the locks later if defaults change?

Athanor provides a heavily extended and modified Lock system to attempt to answer this dilemna.

The `athanor.typeclasses.mixin.AthanorAccess` typeclass mixin provides an advanced LockHandler and .access() method which provides an expanded foundation upon which a greater variety of systems can be built, with several already provided.

The AthanorLockHandler provides a mechanism for allowing each typeclass to define a `dict[access_type, list]` of lockfuncs checked in list order to determine defaults. Athanor's own plugin systems use this for Zone control, if using the Zone plugins. Zone defaults are put at the front of the list for objects that belong to Zones, while the second entry is the default for that Typeclass. The first check that returns a lockdef will be be called.

Additionally, if an object defines an `access_check_<access_type>` method, it will be called to determine if the lock is passed. The `AthanorCharacter` typeclass uses this for `access_check_puppet` to see if accessing_obj is the Account the character belongs to.

Lastly, it's possible to define a series of access_funcs which also respond to access_type.

Between all of these systems, one should only need to explicitly set an actual lock on an object if it's meant to be an exception to the norms, and defaults can be managed in settings.py for easy central management.

### EVENT EMITTER
This is honestly quite simple.

```python
from athanor import emit, register_event, unregister_event

def my_event_handler(*args, **kwargs):
    print(f"I got called! {args}")

register_event("my_event", my_event_handler)

emit("my_event", "boo")

unregister_event("my_event", my_event_handler)
```

It's up to you how to use this. Great way to decouple code across plugins.

### RICH INTEGRATION
Each ServerSession has its own rich.console.Console instance configured to use Evennia's client width and color settings for that session.

`ServerSession.data_out(**kwargs)` has been modified to respond to some very special kwargs, as follows:
  * rich=\<renderable\> - This will render the renderable and send it to the client.
  * markdown=\<str\> - This will render the markdown and send it to the client. Note that some markdown features are not supported; it's telnet, after all.
  * traceback=True - This will render the traceback of the current exception and send it to the client.

Only one of these kwargs should be used at a time. If more than one is used, the last one will be used.

`ServerSession.data_out(**kwargs)` is eventually called by all variants of .msg() on Objects, Accounts, Sessions, and Commands, so, in a command, this could be used with `self.msg(rich=blah)`

## FAQ 
  __Q:__ This is cool! How can I help?  
  __A:__ [Patreon](https://www.patreon.com/volund) support is always welcome. If you can code and have cool ideas or bug fixes, feel free to fork, edit, and pull request! Join our [discord](https://discord.gg/Sxuz3QNU8U) to really get cranking away though.

  __Q:__ I found a bug! What do I do?  
  __A:__ Post it on this GitHub's Issues tracker. I'll see what I can do when I have time. ... or you can try to fix it yourself and submit a Pull Request. That's cool too.

  __Q:__ The heck is an Athanor? Why name something this?
  __A:__ An Athanor is a furnace used in alchemy. It's a place where things are forged and refined. I thought it was a fitting name for a library that's meant to be used to build other things.

## Special Thanks
  * The Evennia Project.
  * All of my Patrons on Patreon.
  * Anyone who contributes to this project or my other ones.
