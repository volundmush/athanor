from .utils import ip_from_request


def django_login_success(sender, **kwargs):
    if not (user := kwargs.get("user", dict())):
        return
    if not (request := kwargs.get("request", None)):
        return
    if not (ip := ip_from_request(request)):
        return
    _login_record(user, ip)


def django_login_fail(sender, **kwargs):
    if not (request := kwargs.get("request", None)):
        return
    if not (ip := ip_from_request(request)):
        return
    if not (credentials := kwargs.get("credentials", dict())):
        return
    if not (username := credentials.get("username", None)):
        return
    from evennia import DefaultAccount

    if not (
        account := DefaultAccount.objects.filter_family(
            username__iexact=username
        ).first()
    ):
        return
    _login_record(
        account,
        ip,
        success=False,
        reason=kwargs.get("reason", "Failed to authenticate."),
    )


def login_success(sender, **kwargs):
    if not (session := kwargs.get("session", None)):
        return
    _login_record(sender, session.address)


def login_fail(sender, **kwargs):
    if not (session := kwargs.get("session", None)):
        return
    _login_record(
        sender,
        session.address,
        success=False,
        reason=kwargs.get("reason", "Failed to authenticate."),
    )


def _login_record(user, ip, success=True, reason=None):
    from athanor.playviews.models import Host

    host, created = Host.objects.get_or_create(ip=ip)
    host.records.create(account=user, is_success=success, reason=reason)
