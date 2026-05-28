from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

NOTAS = {
    'compra': 'Compra a proveedor',
    'consumo': 'Consumo de cocina',
    'merma': 'Merma / pérdida',
    'ajuste': 'Ajuste de inventario',
}


class Command(BaseCommand):
    help = 'Poblar la BD con datos de prueba para Cevichería El Marino'

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from apps.negocios.models import Negocio
        from apps.proveedores.models import Proveedor
        from apps.inventario.models import Producto, Movimiento
        from apps.ventas.models import Venta, DetalleVenta

        User = get_user_model()

        with transaction.atomic():
            negocio = Negocio.objects.get(nombre='Cevichería El Marino')
            user = User.objects.get(email='dueno@marino.com')
            self.stdout.write(f'Negocio: {negocio.nombre}')

            # --- Reset de datos transaccionales (seed re-ejecutable) ---
            Venta.objects.for_tenant(negocio).delete()  # cascada a DetalleVenta
            Movimiento.objects.for_tenant(negocio).delete()
            self.stdout.write('  Ventas y movimientos previos eliminados')

            # --- Proveedores ---
            prov_mariscos, _ = Proveedor.objects.get_or_create(
                negocio=negocio, nombre='Mariscos Don Pedro',
                defaults={'contacto': 'Pedro Loor', 'telefono': '0991234567', 'email': 'pedro@mariscos.ec'}
            )
            prov_verduras, _ = Proveedor.objects.get_or_create(
                negocio=negocio, nombre='Verduras Frescas Guayas',
                defaults={'contacto': 'María Espinoza', 'telefono': '0987654321'}
            )
            prov_bebidas, _ = Proveedor.objects.get_or_create(
                negocio=negocio, nombre='Distribuidora El Litoral',
                defaults={'contacto': 'Carlos Vera', 'telefono': '0976543210'}
            )
            self.stdout.write('  Proveedores: 3 listos')

            # --- Insumos --- clave: (nombre, costo, unidad, stock_min, proveedor)
            insumos_data = {
                'camaron': ('Camarón mediano', Decimal('15.50'), 'kg', Decimal('2'), prov_mariscos),
                'corvina': ('Corvina fresca',  Decimal('18.00'), 'kg', Decimal('1.5'), prov_mariscos),
                'limon':   ('Limón sutil',     Decimal('1.20'),  'kg', Decimal('1'), prov_verduras),
                'cebolla': ('Cebolla paiteña', Decimal('0.90'),  'kg', Decimal('2'), prov_verduras),
                'cerveza': ('Cerveza Pilsener', Decimal('1.50'), 'unidad', Decimal('24'), prov_bebidas),
            }
            insumos = {}
            for clave, (nombre, costo, unidad, stock_min, prov) in insumos_data.items():
                prod, _ = Producto.objects.get_or_create(
                    negocio=negocio, nombre=nombre,
                    defaults={'categoria': 'insumo', 'costo': costo, 'unidad': unidad,
                              'stock_minimo': stock_min, 'proveedor': prov}
                )
                insumos[clave] = prod
            self.stdout.write('  Insumos: 5 listos')

            # --- Platos --- clave: (nombre, precio_venta)
            platos_data = {
                'cev_camaron': ('Ceviche de camarón',           Decimal('7.50')),
                'cev_mixto':   ('Ceviche mixto',                Decimal('9.00')),
                'encebollado': ('Encebollado',                  Decimal('4.50')),
                'arroz':       ('Arroz con menestra y pescado', Decimal('6.00')),
            }
            platos = {}
            for clave, (nombre, precio) in platos_data.items():
                prod, _ = Producto.objects.get_or_create(
                    negocio=negocio, nombre=nombre,
                    defaults={'categoria': 'plato', 'precio_venta': precio, 'unidad': 'porción'}
                )
                platos[clave] = prod
            self.stdout.write('  Platos: 4 listos')

            # Stock de insumos parte de 0 y se reconstruye con los movimientos
            for prod in insumos.values():
                prod.stock_actual = Decimal('0')
                prod.save(update_fields=['stock_actual'])

            # --- Movimientos por día --- (clave_insumo, tipo, motivo, cantidad)
            # Compras = gasto del día; consumos/mermas = salidas de stock.
            # Stock final pensado para dejar 'limon' y 'cebolla' en crítico.
            movimientos_por_dia = {
                2: [  # antier: reabastecimiento inicial
                    ('camaron', 'entrada', 'compra', Decimal('10')),
                    ('corvina', 'entrada', 'compra', Decimal('6')),
                    ('limon',   'entrada', 'compra', Decimal('5')),
                    ('cebolla', 'entrada', 'compra', Decimal('8')),
                    ('cerveza', 'entrada', 'compra', Decimal('48')),
                ],
                1: [  # ayer: reposición + consumos
                    ('camaron', 'entrada', 'compra', Decimal('5')),
                    ('camaron', 'salida',  'consumo', Decimal('4')),
                    ('limon',   'salida',  'consumo', Decimal('2')),
                    ('cebolla', 'salida',  'consumo', Decimal('3')),
                    ('corvina', 'salida',  'merma',   Decimal('0.5')),
                ],
                0: [  # hoy: compra puntual + consumos + merma
                    ('camaron', 'entrada', 'compra',  Decimal('1')),
                    ('limon',   'entrada', 'compra',  Decimal('2')),
                    ('cebolla', 'entrada', 'compra',  Decimal('1')),
                    ('camaron', 'salida',  'consumo', Decimal('3')),
                    ('limon',   'salida',  'consumo', Decimal('4')),
                    ('cebolla', 'salida',  'consumo', Decimal('4')),
                    ('corvina', 'salida',  'consumo', Decimal('2')),
                    ('cerveza', 'salida',  'consumo', Decimal('12')),
                    ('camaron', 'salida',  'merma',   Decimal('0.5')),
                ],
            }
            movs_creados = 0
            for dias_atras, movs in movimientos_por_dia.items():
                fecha = timezone.now() - timedelta(days=dias_atras)
                for clave, tipo, motivo, cantidad in movs:
                    prod = insumos[clave]
                    mov = Movimiento.objects.create(
                        negocio=negocio, producto=prod, tipo=tipo,
                        motivo=motivo, cantidad=cantidad,
                        nota=NOTAS[motivo], creado_por=user,
                    )
                    mov.creado_en = fecha
                    mov.save(update_fields=['creado_en'])
                    delta = cantidad if tipo == 'entrada' else -cantidad
                    Producto.objects.filter(pk=prod.pk).update(
                        stock_actual=F('stock_actual') + delta
                    )
                    movs_creados += 1
            self.stdout.write(f'  Movimientos: {movs_creados} creados')

            # --- Ventas por día --- lista de pedidos; cada pedido: [(clave_plato, cantidad)]
            ventas_por_dia = {
                2: [  # antier
                    [('cev_camaron', Decimal('2')), ('encebollado', Decimal('1'))],
                    [('cev_mixto', Decimal('1'))],
                ],
                1: [  # ayer
                    [('cev_camaron', Decimal('3'))],
                    [('arroz', Decimal('2'))],
                    [('encebollado', Decimal('2')), ('cev_mixto', Decimal('1'))],
                ],
                0: [  # hoy
                    [('cev_camaron', Decimal('2')), ('cev_mixto', Decimal('1'))],
                    [('encebollado', Decimal('3'))],
                    [('arroz', Decimal('2'))],
                    [('cev_mixto', Decimal('1')), ('encebollado', Decimal('1'))],
                ],
            }
            ventas_creadas = 0
            for dias_atras, pedidos in ventas_por_dia.items():
                fecha_base = timezone.now() - timedelta(days=dias_atras)
                for items in pedidos:
                    total = sum(platos[c].precio_venta * cant for c, cant in items)
                    venta = Venta.objects.create(
                        negocio=negocio, total=total, atendido_por=user
                    )
                    venta.fecha = fecha_base
                    venta.save(update_fields=['fecha'])
                    for clave, cant in items:
                        plato = platos[clave]
                        DetalleVenta.objects.create(
                            venta=venta, producto=plato,
                            cantidad=cant, precio_unitario=plato.precio_venta
                        )
                    ventas_creadas += 1
            self.stdout.write(f'  Ventas: {ventas_creadas} creadas')

        self.stdout.write(self.style.SUCCESS('Seed completado.'))
