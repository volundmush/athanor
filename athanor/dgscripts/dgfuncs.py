def id(obj, script, arg):
    return obj.dbref

def name(obj, script, arg):
    return obj.get_display_name(looker=script.handler.owner)

def varexists(obj, script, arg):
    if arg:
        return "1" if arg.lower() in obj.dgscripts.vars[script.context] else "0"
    return "0"
