# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos esenciales

```bash
# Activar entorno virtual (siempre antes de cualquier comando)
source venv/bin/activate

# Servidor de desarrollo
python manage.py runserver

# Migraciones (después de cambiar modelos)
python manage.py makemigrations <app>
python manage.py migrate

# Verificar configuración
python manage.py check

# Crear superusuario para el admin
python manage.py createsuperuser
```

## Base de datos local

PostgreSQL local con usuario de app de mínimos privilegios:
- **Host:** localhost:5432
- **BD:** `ecuainventario`
- **Usuario:** `ecuainventario_app` / `Ecua2026!App`
- Configurado en `.env` vía `DATABASE_URL`

El `.env` no está en git. Copiar `.env.example` y completar `ANTHROPIC_API_KEY` y `OPENAI_API_KEY` para usar el Chat IA.

## Arquitectura

SaaS multitenancy para negocios gastronómicos. Cada negocio es un tenant aislado por FK — **no se usan schemas de PostgreSQL** (decisión de MVP; migrar a `django-tenants` cuando escale).

### Patrón de multitenancy (crítico)

Todo modelo de negocio hereda de `TenantModel` (`apps/core/models.py`):

```python
class TenantModel(models.Model):
    negocio = ForeignKey('negocios.Negocio', on_delete=CASCADE)
    objects = TenantManager()   # .for_tenant(negocio) → QuerySet filtrado
    class Meta:
        abstract = True
```

Todo ViewSet de negocio hereda `TenantViewSetMixin` (`apps/core/views.py`) **antes** de `ModelViewSet`. Este mixin sobreescribe `get_queryset()` para filtrar por `request.user.negocio`. **Nunca omitir este mixin en ViewSets de datos de negocio.**

### Apps y responsabilidades

| App | Contenido |
|---|---|
| `apps/core` | `TenantModel`, `TenantViewSetMixin` — sin URLs ni migraciones propias |
| `apps/autenticacion` | Custom `Usuario` (email como USERNAME_FIELD), JWT registro/login/perfil |
| `apps/negocios` | Modelo `Negocio` (tenant raíz), endpoint GET/PATCH de configuración |
| `apps/inventario` | `Producto` (insumo\|plato) + `Movimiento` (entradas/salidas de insumos) |
| `apps/proveedores` | `Proveedor` con soft-delete (`activo=False`) |
| `apps/ventas` | `Venta` + `DetalleVenta` — ventas de platos a clientes, separadas de movimientos |
| `apps/dashboard` | Vista agregada: ventas del día, alertas de stock bajo, últimos movimientos |
| `apps/chat` | Integración Anthropic + Whisper; toda la lógica en `services.py` |

### Modelo de datos resumido

```
Negocio
├── Usuario (AUTH_USER_MODEL)
├── Proveedor
├── Producto (categoria: insumo|plato)
│   └── Movimiento (solo para insumos — consumo/compra, NO ventas)
└── Venta
    └── DetalleVenta (snapshot de precio_unitario al momento de la venta)
```

**Importante:** `Movimiento` y `Venta` son entidades distintas. Los movimientos trackean stock de insumos; las ventas registran revenue de platos. El dashboard suma `Venta.total` (no movimientos) para el total del día.

### Chat IA (`apps/chat/services.py`)

Flujo: texto/audio/foto → propuesta JSON → usuario confirma → `confirmar_accion()` escribe a BD.

- **LLM:** `claude-haiku-4-5-20251001` vía Anthropic SDK
- **Audio:** Whisper (`whisper-1`) vía OpenAI SDK — transcribe a texto y pasa al LLM
- **Foto:** Claude Haiku con visión (imagen en base64) — extrae datos de facturas
- **El LLM nunca escribe directamente a la BD** — siempre pasa por `/api/chat/confirmar/`

Las 5 acciones que puede proponer el LLM: `registrar_movimiento`, `crear_producto`, `crear_proveedor`, `actualizar_producto`, `registrar_venta`.

`_build_system_prompt()` inyecta el inventario actual del negocio en cada llamada para que el LLM use nombres exactos.

### Autenticación

JWT Bearer token en todos los endpoints excepto `registro/` y `login/`. Configurado globalmente en `REST_FRAMEWORK` — no hace falta declararlo por vista. Access token: 8h. Refresh: 30 días con rotación.

El registro (`POST /api/auth/registro/`) crea `Negocio` + `Usuario` en una transacción atómica y devuelve los tokens directamente.

## Convenciones

- PKs UUID en todos los modelos de negocio (`id = UUIDField(primary_key=True, default=uuid4)`)
- Soft-delete en `Proveedor` y `Producto`: `activo=False`, nunca `DELETE` real
- Stock se actualiza con `F('stock_actual') + delta` dentro de `transaction.atomic()` para evitar race conditions
- `DetalleVenta.subtotal` se recalcula en `save()` — no confiar en el valor que envíe el cliente
- Variables de entorno siempre vía `python-decouple` (`config()`), nunca `os.environ`
