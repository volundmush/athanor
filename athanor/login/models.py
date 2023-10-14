from django.db import models


class Host(models.Model):
    ip = models.GenericIPAddressField(unique=True)
    hostname = models.CharField(max_length=255, unique=True)


class Record(models.Model):
    host = models.ForeignKey(Host, on_delete=models.PROTECT, related_name="records")
    user = models.ForeignKey("accounts.AccountDB", on_delete=models.CASCADE)
    is_success = models.BooleanField(default=False)
    reason = models.CharField(max_length=50, null=True, blank=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=True)
