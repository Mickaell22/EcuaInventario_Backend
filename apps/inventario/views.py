from rest_framework import filters, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from apps.core.views import TenantViewSetMixin
from .models import Movimiento, Producto
from .serializers import (
    MovimientoCreateGlobalSerializer,
    MovimientoCreateSerializer,
    MovimientoSerializer,
    ProductoSerializer,
)


class ProductoViewSet(TenantViewSetMixin, ModelViewSet):
    queryset = Producto.objects.select_related('proveedor').filter(activo=True)
    serializer_class = ProductoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)
        return qs

    def perform_create(self, serializer):
        serializer.save(negocio=self.request.user.negocio)

    def destroy(self, request, *args, **kwargs):
        producto = self.get_object()
        producto.activo = False
        producto.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='movimiento')
    def registrar_movimiento(self, request, pk=None):
        producto = self.get_object()
        serializer = MovimientoCreateSerializer(
            data=request.data,
            context={'request': request, 'producto': producto},
        )
        serializer.is_valid(raise_exception=True)
        movimiento = serializer.save()
        return Response(MovimientoSerializer(movimiento).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='movimientos')
    def historial_movimientos(self, request, pk=None):
        producto = self.get_object()
        movimientos = Movimiento.objects.filter(
            negocio=request.user.negocio, producto=producto
        ).select_related('creado_por')
        serializer = MovimientoSerializer(movimientos, many=True)
        return Response(serializer.data)


class MovimientoViewSet(
    TenantViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Movimiento.objects.select_related('producto', 'creado_por').all()
    serializer_class = MovimientoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['producto__nombre']

    def get_queryset(self):
        qs = super().get_queryset()
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = MovimientoCreateGlobalSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        movimiento = serializer.save()
        return Response(MovimientoSerializer(movimiento).data, status=status.HTTP_201_CREATED)
