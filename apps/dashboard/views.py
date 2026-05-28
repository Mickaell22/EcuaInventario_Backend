from datetime import date as date_type
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventario.models import Movimiento, Producto
from apps.inventario.serializers import MovimientoSerializer, ProductoSerializer
from apps.ventas.models import Venta


class DashboardView(APIView):
    def get(self, request):
        negocio = request.user.negocio

        # Acepta ?fecha=YYYY-MM-DD; sin parámetro usa hoy
        fecha_param = request.query_params.get('fecha')
        if fecha_param:
            try:
                hoy = date_type.fromisoformat(fecha_param)
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Usa YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            hoy = timezone.now().date()

        ingresos = (
            Venta.objects.for_tenant(negocio)
            .filter(fecha__date=hoy)
            .aggregate(total=Sum('total'))['total']
            or Decimal('0')
        )

        # Solo movimientos con motivo='compra' cuentan como gasto real
        # Los ajustes de inventario (motivo='ajuste') no son gastos operativos
        gastos = (
            Movimiento.objects.for_tenant(negocio)
            .filter(creado_en__date=hoy, tipo='entrada', motivo='compra')
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F('cantidad') * F('producto__costo'),
                        output_field=DecimalField(max_digits=14, decimal_places=4),
                    )
                )
            )['total']
            or Decimal('0')
        )

        utilidad = ingresos - gastos

        productos_criticos = Producto.objects.for_tenant(negocio).filter(
            activo=True,
            stock_actual__lte=F('stock_minimo'),
        ).select_related('proveedor')

        ultimos_movimientos = (
            Movimiento.objects.for_tenant(negocio)
            .select_related('producto', 'creado_por')[:10]
        )

        return Response(
            {
                'fecha': hoy.isoformat(),
                'ingresos': ingresos,
                'gastos': gastos,
                'utilidad': utilidad,
                'stock_critico': {
                    'count': productos_criticos.count(),
                    'productos': ProductoSerializer(
                        productos_criticos, many=True, context={'request': request}
                    ).data,
                },
                'ultimos_movimientos': MovimientoSerializer(
                    ultimos_movimientos, many=True
                ).data,
            }
        )
