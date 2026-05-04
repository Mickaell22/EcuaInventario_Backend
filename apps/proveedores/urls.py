from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet

router = DefaultRouter()
router.register('', ProveedorViewSet, basename='proveedor')

urlpatterns = router.urls
