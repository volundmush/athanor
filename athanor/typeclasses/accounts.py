from evennia.accounts.accounts import DefaultAccount


class AthanorAccount(DefaultAccount):

    def is_admin(self) -> bool:
        return self.locks.check_lockstring(self, "perm(Admin)")
