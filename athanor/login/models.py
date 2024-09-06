from django.db import models

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