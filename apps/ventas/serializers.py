from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from apps.inventario.models import Producto
from .models import DetalleVenta, Venta


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal']
        read_only_fields = ['id', 'precio_unitario', 'subtotal']


class DetalleVentaInputSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))


class VentaCreateSerializer(serializers.Serializer):
    nota = serializers.CharField(required=False, default='', allow_blank=True)
    detalles = DetalleVentaInputSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request.user, 'negocio'):
            self.fields['detalles'].child.fields['producto'].queryset = Producto.objects.filter(
                negocio=request.user.negocio, activo=True, categoria='plato'
            )

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError('Se requiere al menos un detalle.')
        return value

    def validate(self, attrs):
        negocio = self.context['request'].user.negocio
        for detalle in attrs['detalles']:
            producto = detalle['producto']
            if producto.negocio != negocio:
                raise serializers.ValidationError(
                    {'detalles': f'El producto "{producto.nombre}" no pertenece a este negocio.'}
                )
            if producto.categoria != 'plato':
                raise serializers.ValidationError(
                    {'detalles': f'"{producto.nombre}" es un insumo, no se puede vender directamente.'}
                )
            if producto.precio_venta is None:
                raise serializers.ValidationError(
                    {'detalles': f'"{producto.nombre}" no tiene precio de venta definido.'}
                )
        return attrs

    def create(self, validated_data):
        negocio = self.context['request'].user.negocio
        usuario = self.context['request'].user
        detalles_data = validated_data.pop('detalles')

        with transaction.atomic():
            total = Decimal('0')
            detalles_objs = []

            for item in detalles_data:
                producto = item['producto']
                cantidad = item['cantidad']
                precio = producto.precio_venta
                subtotal = cantidad * precio
                total += subtotal
                detalles_objs.append(
                    DetalleVenta(
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio,
                        subtotal=subtotal,
                    )
                )

            venta = Venta.objects.create(
                negocio=negocio,
                atendido_por=usuario,
                total=total,
                **validated_data,
            )

            for d in detalles_objs:
                d.venta = venta
            DetalleVenta.objects.bulk_create(detalles_objs)

        venta.refresh_from_db()
        return venta


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    atendido_por_nombre = serializers.CharField(source='atendido_por.nombre', read_only=True)

    class Meta:
        model = Venta
        fields = ['id', 'fecha', 'total', 'nota', 'atendido_por_nombre', 'detalles']
