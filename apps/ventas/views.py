from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.mixins import CreateModelMixin

from apps.core.views import TenantViewSetMixin
from .models import Venta
from .serializers import VentaCreateSerializer, VentaSerializer


class VentaViewSet(TenantViewSetMixin, CreateModelMixin, ReadOnlyModelViewSet):
    queryset = Venta.objects.prefetch_related('detalles__producto').select_related('atendido_por')
    serializer_class = VentaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        fecha = self.request.query_params.get('fecha')
        if fecha:
            qs = qs.filter(fecha__date=fecha)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = VentaCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        venta = serializer.save()
        return Response(VentaSerializer(venta).data, status=status.HTTP_201_CREATED)
