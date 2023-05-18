from evennia.utils.utils import is_iter, make_iter


def get_objs_with_key_or_alias(self, ostring, exact=True, candidates=None, typeclasses=None):
    if not hasattr(self, "looker"):
        return self.old_get_objs_with_key_or_alias(ostring, exact=exact, candidates=candidates, typeclasses=typeclasses)
    if not isinstance(ostring, str):
        if hasattr(ostring, "key"):
            ostring = ostring.key
        else:
            return self.none()
    if not candidates:
        return self.none()
    if is_iter(candidates) and not len(candidates):
        # if candidates is an empty iterable there can be no matches
        # Exit early.
        return self.none()

    typeclasses = make_iter(typeclasses)

    def filter_typeclasses(candi):
        for candidate in candi:
            if typeclasses:
                if candidate.typeclass_path in typeclasses:
                    yield candidate
            else:
                yield candidate

    return [obj for obj in filter_typeclasses(candidates) if obj.check_search_match(looker=self.looker, ostring=ostring,
                                                                exact=exact)]
