from django.urls import path, include

urlpatterns = [
    path("bbs", include("athanor.boards.urls")),
]
