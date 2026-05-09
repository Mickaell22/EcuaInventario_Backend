from rest_framework.routers import DefaultRouter

from .views import MovimientoViewSet, ProductoViewSet

router = DefaultRouter()
router.register('productos', ProductoViewSet, basename='producto')
router.register('movimientos', MovimientoViewSet, basename='movimiento')

urlpatterns = router.urls
