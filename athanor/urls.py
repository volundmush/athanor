from django.conf import settings
from django.urls import include, path

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

urlpatterns = [path(pattern, include(p)) for pattern, p in settings.URL_INCLUDES]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
