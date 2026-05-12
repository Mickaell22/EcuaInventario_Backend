# CLAUDE.md — EcuaInventario Backend

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

**`DATABASE_URL` es obligatorio** — si no está seteada el servidor falla explícito (el fallback a SQLite fue eliminado intencionalmente).

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
| `apps/autenticacion` | Custom `Usuario` (email como USERNAME_FIELD), JWT registro/login/perfil/cambiar-password |
| `apps/negocios` | Modelo `Negocio` (tenant raíz), endpoint GET/PATCH de configuración |
| `apps/inventario` | `Producto` (insumo\|plato) + `Movimiento` (entradas/salidas de insumos con campo `motivo`) |
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
│   └── Movimiento (solo para insumos — motivo: compra|ajuste|consumo|merma)
└── Venta
    └── DetalleVenta (snapshot de precio_unitario al momento de la venta)
```

**Importante:** `Movimiento` y `Venta` son entidades distintas. Los movimientos trackean stock de insumos; las ventas registran revenue de platos. El dashboard suma `Venta.total` (no movimientos) para los ingresos del día, y solo cuenta como gastos los movimientos con `motivo='compra'` (los ajustes de inventario NO son gastos).

### Chat IA (`apps/chat/services.py`)

Flujo: texto/audio/foto → propuesta JSON → usuario confirma → `confirmar_accion()` escribe a BD.

- **LLM:** `claude-haiku-4-5-20251001` vía Anthropic SDK — timeout 30s
- **Audio:** Whisper (`whisper-1`) vía OpenAI SDK — timeout 60s
- **Foto:** Claude Haiku con visión (imagen en base64) — timeout 30s
- **El LLM nunca escribe directamente a la BD** — siempre pasa por `/api/chat/confirmar/`
- **Archivos permitidos:** audio (mp3/mp4/wav/ogg/webm, máx 10 MB), foto (jpg/png/webp, máx 5 MB)

Las 5 acciones que puede proponer el LLM: `registrar_movimiento`, `crear_producto`, `crear_proveedor`, `actualizar_producto`, `registrar_venta`.

`_build_system_prompt()` inyecta el inventario actual del negocio en cada llamada.

Todas las vistas del chat (`ChatMensajeView`, `ChatAudioView`, `ChatFotoView`, `ChatConfirmarView`) tienen `throttle_classes = [ChatRateThrottle]`.

### Autenticación y seguridad

- JWT Bearer token en todos los endpoints excepto `registro/` y `login/`.
- Access token: 8h. Refresh: 30d con rotación automática.
- **Blacklist activa:** `BLACKLIST_AFTER_ROTATION=True` — los refresh tokens rotados quedan invalidados.
- `CambiarPasswordView` invalida **todos** los refresh tokens activos del usuario al cambiar contraseña.
- **Rate limiting:** anónimos 20/hora, usuarios 1000/día, chat 30/hora (`ChatRateThrottle`).
- Password mínimo: **8 caracteres**.

### Respuesta de login (`POST /api/auth/login/`)

```json
{
  "access": "...",
  "refresh": "...",
  "usuario": { "id", "email", "nombre", "apellido" },
  "negocio": { "id", "nombre", "tipo", "seed_color", "theme_mode" }
}
```

### Dashboard (`GET /api/dashboard/?fecha=YYYY-MM-DD`)

Sin parámetro = hoy. Respuesta:

```json
{
  "fecha": "YYYY-MM-DD",
  "ingresos": "Decimal",
  "gastos": "Decimal",
  "utilidad": "Decimal",
  "stock_critico": { "count": 0, "productos": [...] },
  "ultimos_movimientos": [
    { "id", "tipo", "motivo", "cantidad", "nota", "producto_nombre", "creado_por_nombre", "creado_en" }
  ]
}
```

### Registro (`POST /api/auth/registro/`)

Acepta `negocio_seed_color` (hex `#RRGGBB`, default `#1976D2`) para persistir el color de marca elegido en el onboarding del frontend.

## Convenciones

- PKs UUID en todos los modelos de negocio (`id = UUIDField(primary_key=True, default=uuid4)`)
- Soft-delete en `Proveedor` y `Producto`: `activo=False`, nunca `DELETE` real
- Stock se actualiza con `F('stock_actual') + delta` dentro de `transaction.atomic()` + `select_for_update()` para evitar race conditions
- `DetalleVenta.subtotal` se recalcula en `save()` — no confiar en el valor del cliente
- Variables de entorno siempre vía `python-decouple` (`config()`), nunca `os.environ`
- Errores de servicios externos (Claude, Whisper) se loggean con `logger.exception()` y devuelven mensaje genérico al cliente — nunca `str(e)` en producción
