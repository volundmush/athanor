"""
This is the starting point when a user enters a url in their web browser.

The urls is matched (by regex) and mapped to a 'view' - a Python function or
callable class that in turn (usually) makes use of a 'template' (a html file
with slots that can be replaced by dynamic content) in order to render a HTML
page to show the user.

This file includes the urls in website, webclient and admin. To override you
should modify urls.py in those sub directories.

Search the Django documentation for "URL dispatcher" for more help.

"""
from django.urls import include, path

from web.urls import urlpatterns as web_default_urlpatterns

# add patterns
urlpatterns = [
    path("athanor/", include("athanor.web.urls")),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + web_default_urlpatterns
