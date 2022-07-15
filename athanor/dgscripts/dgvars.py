def self(script, member: str = "", call: bool = False, arg: str = ""):
    return script.handler.owner.dbref

this = self

me = self

def here(script, member: str = "", call: bool = False, arg: str = ""):
    if (room := script.handler.owner.get_room_location()):
        return room.dbref
    return ""
