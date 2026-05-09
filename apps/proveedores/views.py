from rest_framework import filters, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.views import TenantViewSetMixin
from .models import Proveedor
from .serializers import ProveedorSerializer


class ProveedorViewSet(TenantViewSetMixin, ModelViewSet):
    queryset = Proveedor.objects.filter(activo=True)
    serializer_class = ProveedorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'contacto']

    def perform_create(self, serializer):
        serializer.save(negocio=self.request.user.negocio)

    def destroy(self, request, *args, **kwargs):
        proveedor = self.get_object()
        proveedor.activo = False
        proveedor.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)
