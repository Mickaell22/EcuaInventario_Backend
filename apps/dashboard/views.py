from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventario.models import Movimiento, Producto
from apps.inventario.serializers import MovimientoSerializer, ProductoSerializer
from apps.ventas.models import Venta


class DashboardView(APIView):
    def get(self, request):
        negocio = request.user.negocio
        hoy = timezone.now().date()

        total_ventas_hoy = (
            Venta.objects.for_tenant(negocio)
            .filter(fecha__date=hoy)
            .aggregate(total=Sum('total'))['total']
            or 0
        )

        alertas_stock = Producto.objects.for_tenant(negocio).filter(
            activo=True,
            stock_actual__lte=F('stock_minimo'),
        ).select_related('proveedor')

        ultimos_movimientos = (
            Movimiento.objects.for_tenant(negocio)
            .select_related('producto', 'creado_por')[:10]
        )

        return Response(
            {
                'total_ventas_hoy': total_ventas_hoy,
                'alertas_stock': ProductoSerializer(
                    alertas_stock, many=True, context={'request': request}
                ).data,
                'ultimos_movimientos': MovimientoSerializer(
                    ultimos_movimientos, many=True
                ).data,
            }
        )
