from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet

router = DefaultRouter()
router.register('', ProductoViewSet, basename='producto')

urlpatterns = router.urls
