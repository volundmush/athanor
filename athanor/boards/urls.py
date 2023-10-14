from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"collections", views.BoardCollectionViewSet)
router.register(r"boards", views.BoardViewSet)
router.register(r"posts", views.PostViewSet)

urlpatterns = router.urls
