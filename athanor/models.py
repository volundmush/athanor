from django.db import models


class AccountPlaytime(models.Model):
    id = models.OneToOneField(
        "accounts.AccountDB",
        primary_key=True,
        related_name="playtime",
        on_delete=models.CASCADE,
    )
    total_playtime = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CharacterPlaytime(models.Model):
    id = models.OneToOneField(
        "objects.ObjectDB",
        primary_key=True,
        related_name="+",
        on_delete=models.CASCADE,
    )
    total_playtime = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CharacterAccountPlaytime(models.Model):
    playtime = models.ForeignKey(
        CharacterPlaytime, on_delete=models.CASCADE, related_name="per_account"
    )
    account = models.ForeignKey(
        "accounts.AccountDB",
        on_delete=models.CASCADE,
        related_name="characters_playtime",
    )
    total_playtime = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("playtime", "account")


class AccountOwner(models.Model):
    id = models.OneToOneField(
        "objects.ObjectDB",
        primary_key=True,
        related_name="account_owner",
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        "accounts.AccountDB", related_name="owned_characters", on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.id)


class Host(models.Model):
    ip = models.GenericIPAddressField(unique=True)
    hostname = models.CharField(max_length=255, null=True)


class LoginRecord(models.Model):
    host = models.ForeignKey(Host, on_delete=models.PROTECT, related_name="records")
    account = models.ForeignKey(
        "accounts.AccountDB", on_delete=models.CASCADE, related_name="login_records"
    )
    is_success = models.BooleanField(default=False)
    reason = models.CharField(max_length=50, null=True, blank=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=True)
