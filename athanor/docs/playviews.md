# Playviews
Athanor's playviews heavily interact with and alter the assumptions made by [Evennia's Connection Styles](https://www.evennia.com/docs/latest/Concepts/Connection-Styles.html#multisession-mode-and-multi-playing) concepts. It is recommended to read up on those before this.

# The Problem(TM)
Evennia's concept of "puppeting" Objects is amazing; so little links a Session to an Object/Character and yet, so much stands in the way of elegantly orchestrating this relationship in the default approach. Athanor envisions MUDs which may feature vehicles, summoned entities, quests that control alternate characters and numerous other things which would involve relaying commands to an object OTHER than the chosen player character, but without putting the original player character in an 'offline' state.

Additionally, many commands may depend on being attached to an Object and also having a Session, which are only useful in the context of a player character OR a specific "session of play" (IE: goes away when you log out.) Furthermore, many games may want to implement special behaviors to be triggered when unexpected disconnections happen in the middle of play. Evennia also puts all logic governing the different states of login/logout, logic to change between those states and other things on the Character typeclass by default. If you develop from there towards a direction of using different typeclassees for characters and non-player characters, managing the class hierarchy could get quite complex.

# Athanor's Solution
The Playview acts as a kind of 'middleman' between Sessions and Objects, when a character is IC/puppeted. Multiple Sessions can link to the one Playview and the Playview manages linking the puppet to the Session(s). The Playview can 'switch puppets' at any time and it will affect all connected Sessions. New sessions may attempt to attach to the 'character' and will still be using whatever puppet the playview has configured at the moment.

It has its own CmdSetHandler and acts as a fourth provider of Commands (the others being Session, Account, and Object) now in the order of "Session -> Account -> Playview -> Object." Playviews are created when a player character "goes IC" and remain until the player character "fully logs out" (normally meaning , all sessions have disconnected or the QUIT command is used.)

Additionally, the Playview handles the entire sequence of logging in and logging out of the game, such as stowing characters in nullspace and sending announcements to the relevant rooms. These are now customizable and completely separated from the Character typeclass, freeing it to be developed towards any purposes desired and shifting complexity away.

The Playview is a fully typeclassed entity, which means it can be inherited from, the BASE_PLAYVIEW_TYPECLASS changed, and it has support for tags, attributes, and similar niceties.

Because the Playview lasts only as long as needed, it can survive reloads - meaning its .db attributes are persistent as long as needed, unlike Sessions - but it's deleted when characters log out. This makes it IDEAL for storing temporary data that needs to persist across reloads but not across logins. Delete the playview and it neatly deletes all of that data without affecting the Character object.