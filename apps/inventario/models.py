import uuid
from django.db import models
from apps.core.models import TenantModel


class Producto(TenantModel):
    CATEGORIA_CHOICES = [
        ('insumo', 'Insumo'),
        ('plato', 'Plato'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=120)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_actual = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    unidad = models.CharField(max_length=20, default='unidad')
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    proveedor = models.ForeignKey(
        'proveedores.Proveedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'producto'
        verbose_name_plural = 'productos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_categoria_display()})'


class Movimiento(TenantModel):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='movimientos',
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    nota = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        'autenticacion.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='movimientos',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'movimiento'
        verbose_name_plural = 'movimientos'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.tipo} de {self.producto.nombre} — {self.cantidad}'
