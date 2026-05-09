from decimal import Decimal
from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from .models import Movimiento, Producto


class ProductoSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(
        source='proveedor.nombre', read_only=True, default=None
    )
    stock_bajo = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'categoria', 'precio_venta', 'costo',
            'stock_actual', 'unidad', 'stock_minimo',
            'proveedor', 'proveedor_nombre', 'stock_bajo', 'activo',
        ]
        read_only_fields = ['id', 'stock_actual']

    def get_stock_bajo(self, obj):
        return obj.stock_actual <= obj.stock_minimo

    def validate_proveedor(self, proveedor):
        if proveedor is None:
            return proveedor
        negocio = self.context['request'].user.negocio
        if proveedor.negocio != negocio:
            raise serializers.ValidationError('El proveedor no pertenece a este negocio.')
        return proveedor


class MovimientoSerializer(serializers.ModelSerializer):
    creado_por_nombre = serializers.CharField(source='creado_por.nombre', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = Movimiento
        fields = ['id', 'tipo', 'cantidad', 'nota', 'producto_nombre', 'creado_por_nombre', 'creado_en']
        read_only_fields = ['id', 'creado_en']


class MovimientoCreateSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=['entrada', 'salida'])
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    nota = serializers.CharField(required=False, default='', allow_blank=True)

    def validate(self, attrs):
        producto = self.context['producto']
        if attrs['tipo'] == 'salida' and producto.stock_actual < attrs['cantidad']:
            raise serializers.ValidationError(
                {'cantidad': f'Stock insuficiente. Disponible: {producto.stock_actual}'}
            )
        return attrs

    def create(self, validated_data):
        producto = self.context['producto']
        negocio = self.context['request'].user.negocio
        usuario = self.context['request'].user

        delta = validated_data['cantidad']
        if validated_data['tipo'] == 'salida':
            delta = -delta

        with transaction.atomic():
            producto_lock = Producto.objects.select_for_update().get(pk=producto.pk)
            if validated_data['tipo'] == 'salida' and producto_lock.stock_actual < validated_data['cantidad']:
                raise serializers.ValidationError(
                    {'cantidad': f'Stock insuficiente. Disponible: {producto_lock.stock_actual}'}
                )
            movimiento = Movimiento.objects.create(
                negocio=negocio,
                producto=producto_lock,
                creado_por=usuario,
                **validated_data,
            )
            Producto.objects.filter(pk=producto.pk).update(
                stock_actual=F('stock_actual') + delta
            )
        return movimiento


class MovimientoCreateGlobalSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.none())
    tipo = serializers.ChoiceField(choices=['entrada', 'salida'])
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    nota = serializers.CharField(required=False, default='', allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request.user, 'negocio'):
            self.fields['producto'].queryset = Producto.objects.filter(
                negocio=request.user.negocio, activo=True, categoria='insumo'
            )

    def validate(self, attrs):
        if attrs['tipo'] == 'salida' and attrs['producto'].stock_actual < attrs['cantidad']:
            raise serializers.ValidationError(
                {'cantidad': f'Stock insuficiente. Disponible: {attrs["producto"].stock_actual}'}
            )
        return attrs

    def create(self, validated_data):
        producto = validated_data.pop('producto')
        negocio = self.context['request'].user.negocio
        usuario = self.context['request'].user

        delta = validated_data['cantidad']
        if validated_data['tipo'] == 'salida':
            delta = -delta

        with transaction.atomic():
            producto_lock = Producto.objects.select_for_update().get(pk=producto.pk)
            if validated_data['tipo'] == 'salida' and producto_lock.stock_actual < validated_data['cantidad']:
                raise serializers.ValidationError(
                    {'cantidad': f'Stock insuficiente. Disponible: {producto_lock.stock_actual}'}
                )
            movimiento = Movimiento.objects.create(
                negocio=negocio,
                producto=producto_lock,
                creado_por=usuario,
                **validated_data,
            )
            Producto.objects.filter(pk=producto_lock.pk).update(
                stock_actual=F('stock_actual') + delta
            )
        return movimiento
