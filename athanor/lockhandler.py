from evennia.locks.lockhandler import LockHandler


class AthanorLockHandler(LockHandler):
    _lock_cache = dict()

    def _parse_lockstring(self, storage_lockstring: str):
        if not storage_lockstring:
            return super()._parse_lockstring(storage_lockstring)
        if storage_lockstring in self._lock_cache:
            return self._lock_cache[storage_lockstring]
        locks = super()._parse_lockstring(storage_lockstring)
        self._lock_cache[storage_lockstring] = locks
        return locks

    def check(
        self, accessing_obj, access_type, default=False, no_superuser_bypass=False
    ):
        """
        Checks a lock of the correct type by passing execution off to
        the lock function(s).

        Args:
            accessing_obj (object): The object seeking access.
            access_type (str): The type of access wanted.
            default (bool, optional): If no suitable lock type is
                found, default to this result.
            no_superuser_bypass (bool): Don't use this unless you
                really, really need to, it makes supersusers susceptible
                to the lock check.

        Notes:
            A lock is executed in the follwoing way:

            Parsing the lockstring, we (during cache) extract the valid
            lock functions and store their function objects in the right
            order along with their args/kwargs. These are now executed in
            sequence, creating a list of True/False values. This is put
            into the evalstring, which is a string of AND/OR/NOT entries
            separated by placeholders where each function result should
            go. We just put those results in and evaluate the string to
            get a final, combined True/False value for the lockstring.

            The important bit with this solution is that the full
            lockstring is never blindly evaluated, and thus there (should
            be) no way to sneak in malign code in it. Only "safe" lock
            functions (as defined by your settings) are executed.

        """
        try:
            # check if the lock should be bypassed (e.g. superuser status)
            if accessing_obj.locks.lock_bypass and not no_superuser_bypass:
                return True
        except AttributeError:
            # happens before session is initiated.
            if not no_superuser_bypass and (
                (hasattr(accessing_obj, "is_superuser") and accessing_obj.is_superuser)
                or (
                    hasattr(accessing_obj, "account")
                    and hasattr(accessing_obj.account, "is_superuser")
                    and accessing_obj.account.is_superuser
                )
                or (
                    hasattr(accessing_obj, "get_account")
                    and (
                        not accessing_obj.get_account()
                        or accessing_obj.get_account().is_superuser
                    )
                )
            ):
                return True

        # no superuser or bypass -> normal lock operation
        if lockdef := self.locks.get(access_type, self.obj.get_lockdef(access_type)):
            # we have a lock, test it.
            evalstring, func_tup, raw_string = lockdef
            # execute all lock funcs in the correct order, producing a tuple of True/False results.
            true_false = tuple(
                bool(tup[0](accessing_obj, self.obj, *tup[1], **tup[2]))
                for tup in func_tup
            )
            # the True/False tuple goes into evalstring, which combines them
            # with AND/OR/NOT in order to get the final result.
            return eval(evalstring % true_false)
        else:
            return default
