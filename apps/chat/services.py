import base64
import json
import re
from datetime import date
from decimal import Decimal

from anthropic import Anthropic
from django.conf import settings
from django.db import transaction
from django.db.models import F
from openai import OpenAI

from apps.inventario.models import Movimiento, Producto
from apps.proveedores.models import Proveedor
from apps.ventas.models import DetalleVenta, Venta

MODELO_HAIKU = 'claude-haiku-4-5-20251001'


# ── Contexto y prompt ────────────────────────────────────────────────────────

def _build_system_prompt(negocio):
    productos = Producto.objects.for_tenant(negocio).filter(activo=True).values(
        'nombre', 'categoria', 'stock_actual', 'unidad'
    )
    proveedores = Proveedor.objects.for_tenant(negocio).filter(activo=True).values_list(
        'nombre', flat=True
    )

    productos_txt = '\n'.join(
        f"- {p['nombre']} ({p['categoria']}, stock: {p['stock_actual']} {p['unidad']})"
        for p in productos
    ) or '(ninguno registrado)'

    proveedores_txt = '\n'.join(f'- {n}' for n in proveedores) or '(ninguno registrado)'

    return f"""Eres un asistente de gestión de inventario para negocios gastronómicos en Ecuador.
Responde SOLO con un JSON válido, sin texto adicional ni bloques de código markdown.

NEGOCIO: {negocio.nombre} ({negocio.tipo})
FECHA: {date.today().strftime('%d/%m/%Y')}

PRODUCTOS REGISTRADOS:
{productos_txt}

PROVEEDORES REGISTRADOS:
{proveedores_txt}

ACCIONES DISPONIBLES:
1. registrar_movimiento — entradas o salidas de insumos
   datos: producto(nombre), tipo(entrada|salida), cantidad(número), nota(opcional)

2. crear_producto — agregar nuevo producto o insumo
   datos: nombre, categoria(insumo|plato), costo, unidad, stock_minimo, precio_venta(solo platos)

3. crear_proveedor — registrar nuevo proveedor
   datos: nombre, telefono(opcional), email(opcional), contacto(opcional)

4. actualizar_producto — modificar datos de un producto existente
   datos: producto(nombre actual), campos a actualizar(precio_venta, costo, stock_minimo, unidad)

5. registrar_venta — registrar venta de platos a clientes
   datos: detalles([{{"producto": nombre, "cantidad": número}}]), nota(opcional)

FORMATO DE RESPUESTA:
{{
  "accion": "<accion>",
  "datos": {{ ... }},
  "resumen": "<descripción breve en español de lo que se hará>"
}}

Si el mensaje no corresponde a ninguna acción responde con accion "no_reconocido" y explica amablemente en "resumen" qué puede hacer el asistente."""


def _parse_llm_response(text):
    text = re.sub(r'```(?:json)?\s*', '', text).strip('`').strip()
    return json.loads(text)


# ── Procesamiento de entrada ─────────────────────────────────────────────────

def procesar_mensaje(texto, negocio):
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=MODELO_HAIKU,
        max_tokens=512,
        system=_build_system_prompt(negocio),
        messages=[{'role': 'user', 'content': texto}],
    )
    return _parse_llm_response(message.content[0].text)


def transcribir_audio(audio_file):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    transcript = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file,
        language='es',
    )
    return transcript.text


def procesar_foto(imagen_file, negocio):
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    image_data = base64.standard_b64encode(imagen_file.read()).decode('utf-8')
    media_type = imagen_file.content_type or 'image/jpeg'

    message = client.messages.create(
        model=MODELO_HAIKU,
        max_tokens=512,
        system=_build_system_prompt(negocio),
        messages=[
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': image_data,
                        },
                    },
                    {
                        'type': 'text',
                        'text': 'Analiza esta factura o recibo y extrae los datos para registrar el movimiento o venta correspondiente.',
                    },
                ],
            }
        ],
    )
    return _parse_llm_response(message.content[0].text)


# ── Búsquedas internas ───────────────────────────────────────────────────────

def _buscar_producto(nombre, negocio):
    qs = Producto.objects.for_tenant(negocio).filter(activo=True)
    try:
        return qs.get(nombre__iexact=nombre)
    except Producto.DoesNotExist:
        matches = qs.filter(nombre__icontains=nombre)
        if matches.count() == 1:
            return matches.first()
        raise ValueError(f'Producto "{nombre}" no encontrado. Verifica el nombre en el inventario.')


def _buscar_proveedor(nombre, negocio):
    if not nombre:
        return None
    qs = Proveedor.objects.for_tenant(negocio).filter(activo=True)
    try:
        return qs.get(nombre__iexact=nombre)
    except Proveedor.DoesNotExist:
        matches = qs.filter(nombre__icontains=nombre)
        return matches.first()


# ── Confirmación de acciones ─────────────────────────────────────────────────

def confirmar_accion(propuesta, negocio, usuario):
    accion = propuesta.get('accion')
    datos = propuesta.get('datos', {})

    handlers = {
        'registrar_movimiento': _confirmar_movimiento,
        'crear_producto': _confirmar_crear_producto,
        'crear_proveedor': _confirmar_crear_proveedor,
        'actualizar_producto': _confirmar_actualizar_producto,
        'registrar_venta': _confirmar_venta,
    }

    handler = handlers.get(accion)
    if not handler:
        raise ValueError(f'Acción no reconocida: "{accion}"')

    if accion in ('registrar_movimiento', 'registrar_venta'):
        return handler(datos, negocio, usuario)
    return handler(datos, negocio)


def _format_for_flutter(propuesta):
    return {
        'ok': True,
        'accion': propuesta.get('accion'),
        'resumen': propuesta.get('resumen', ''),
        'datos': propuesta.get('datos', {}),
    }


def _confirmar_movimiento(datos, negocio, usuario):
    producto = _buscar_producto(datos['producto'], negocio)
    tipo = datos['tipo']
    cantidad = Decimal(str(datos['cantidad']))
    nota = datos.get('nota', '')
    delta = cantidad if tipo == 'entrada' else -cantidad

    with transaction.atomic():
        producto_lock = Producto.objects.select_for_update().get(pk=producto.pk)
        if tipo == 'salida' and producto_lock.stock_actual < cantidad:
            raise ValueError(
                f'Stock insuficiente. Disponible: {producto_lock.stock_actual} {producto_lock.unidad}'
            )
        movimiento = Movimiento.objects.create(
            negocio=negocio,
            producto=producto_lock,
            tipo=tipo,
            cantidad=cantidad,
            nota=nota,
            creado_por=usuario,
        )
        Producto.objects.filter(pk=producto_lock.pk).update(stock_actual=F('stock_actual') + delta)

    return {
        'ok': True,
        'tipo': 'movimiento',
        'id': str(movimiento.id),
        'detalle': f'{tipo.capitalize()} de {cantidad} {producto.unidad} de {producto.nombre} registrada.',
    }


def _confirmar_crear_producto(datos, negocio):
    proveedor = _buscar_proveedor(datos.get('proveedor'), negocio)

    producto = Producto.objects.create(
        negocio=negocio,
        nombre=datos['nombre'],
        categoria=datos.get('categoria', 'insumo'),
        costo=Decimal(str(datos.get('costo', 0))),
        unidad=datos.get('unidad', 'unidad'),
        stock_minimo=Decimal(str(datos.get('stock_minimo', 0))),
        precio_venta=Decimal(str(datos['precio_venta'])) if datos.get('precio_venta') else None,
        proveedor=proveedor,
    )
    return {
        'ok': True,
        'tipo': 'producto',
        'id': str(producto.id),
        'detalle': f'Producto "{producto.nombre}" creado correctamente.',
    }


def _confirmar_crear_proveedor(datos, negocio):
    proveedor = Proveedor.objects.create(
        negocio=negocio,
        nombre=datos['nombre'],
        telefono=datos.get('telefono', ''),
        email=datos.get('email', ''),
        contacto=datos.get('contacto', ''),
    )
    return {
        'ok': True,
        'tipo': 'proveedor',
        'id': str(proveedor.id),
        'detalle': f'Proveedor "{proveedor.nombre}" creado correctamente.',
    }


def _confirmar_actualizar_producto(datos, negocio):
    producto = _buscar_producto(datos['producto'], negocio)
    campos_decimales = {'precio_venta', 'costo', 'stock_minimo'}
    campos_permitidos = campos_decimales | {'unidad', 'nombre'}

    for campo, valor in datos.items():
        if campo == 'producto' or campo not in campos_permitidos:
            continue
        setattr(producto, campo, Decimal(str(valor)) if campo in campos_decimales else valor)

    producto.save()
    return {
        'ok': True,
        'tipo': 'producto',
        'id': str(producto.id),
        'detalle': f'Producto "{producto.nombre}" actualizado correctamente.',
    }


def _confirmar_venta(datos, negocio, usuario):
    detalles_data = datos.get('detalles', [])
    if not detalles_data:
        raise ValueError('La venta requiere al menos un producto.')

    with transaction.atomic():
        total = Decimal('0')
        detalles_objs = []

        for item in detalles_data:
            producto = _buscar_producto(item['producto'], negocio)
            if producto.precio_venta is None:
                raise ValueError(f'"{producto.nombre}" no tiene precio de venta definido.')
            cantidad = Decimal(str(item['cantidad']))
            subtotal = cantidad * producto.precio_venta
            total += subtotal
            detalles_objs.append(
                DetalleVenta(
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio_venta,
                    subtotal=subtotal,
                )
            )

        venta = Venta.objects.create(
            negocio=negocio,
            atendido_por=usuario,
            total=total,
            nota=datos.get('nota', ''),
        )
        for d in detalles_objs:
            d.venta = venta
        DetalleVenta.objects.bulk_create(detalles_objs)

    return {
        'ok': True,
        'tipo': 'venta',
        'id': str(venta.id),
        'detalle': f'Venta de ${total} registrada correctamente.',
    }
