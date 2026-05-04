# Backend — Plan de Desarrollo

Plataforma SaaS gastronómica para pequeños negocios de comida en Ecuador. Este documento define el alcance, decisiones y plan de ejecución del backend en Django REST Framework.

---

## Contexto

- SaaS multitenancy: varios negocios usan el mismo backend, cada uno aislado por tenant.
- El frontend móvil (Flutter) ya está implementado con datos mock. Al conectar el backend, los mocks se reemplazan con llamadas reales.
- El chat IA es el canal diferenciador: interpreta texto, audio (vía Whisper) y fotos de facturas (vía Claude Haiku), pero **nunca escribe a la BD sin confirmación humana**.
- Deploy en Railway desde el inicio.

---

## Stack

| Área | Decisión |
|---|---|
| Framework | Django 5 + Django REST Framework |
| Base de datos | PostgreSQL 16 |
| Autenticación | JWT (`djangorestframework-simplejwt`) |
| IA — Chat y Visión | Claude Haiku (`anthropic` SDK) |
| IA — Transcripción de audio | Whisper (`openai` SDK) |
| Variables de entorno | `python-decouple` |
| CORS | `django-cors-headers` |
| Deploy | Railway |
| Servidor de producción | Gunicorn |

---

## Modelo de datos

### Entidades principales

```
Negocio (tenant)
├── Usuario (dueño/empleado del negocio)
├── Producto / Insumo
│   └── Movimiento (entrada / salida de stock)
└── Proveedor
```

### Tablas

#### `negocios_negocio`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| nombre | varchar(120) | |
| tipo | varchar(40) | restaurante, cevichería, etc. |
| seed_color | varchar(7) | hex p.ej. `#1976D2` |
| theme_mode | varchar(10) | `light`, `dark`, `system` |
| creado_en | timestamp | |

#### `auth_usuario` (custom User)
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| negocio | FK → Negocio | tenant |
| email | varchar | único, se usa como username |
| nombre | varchar(80) | |
| apellido | varchar(80) | |
| is_active | bool | |

#### `inventario_producto`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| negocio | FK → Negocio | |
| nombre | varchar(120) | |
| categoria | varchar(20) | `insumo`, `plato` |
| precio_venta | decimal(10,2) | nullable para insumos |
| costo | decimal(10,2) | |
| stock_actual | decimal(10,3) | |
| unidad | varchar(20) | kg, l, unidad, etc. |
| stock_minimo | decimal(10,3) | alerta cuando baje de aquí |
| proveedor | FK → Proveedor | nullable |
| activo | bool | |

#### `inventario_movimiento`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| negocio | FK → Negocio | |
| producto | FK → Producto | |
| tipo | varchar(10) | `entrada`, `salida` |
| cantidad | decimal(10,3) | |
| nota | text | nullable |
| creado_por | FK → Usuario | |
| creado_en | timestamp | |

#### `proveedores_proveedor`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| negocio | FK → Negocio | |
| nombre | varchar(120) | |
| contacto | varchar(80) | nullable |
| telefono | varchar(20) | nullable |
| email | varchar | nullable |
| direccion | text | nullable |
| activo | bool | |

---

## Multitenancy

Cada modelo de negocio tiene FK a `Negocio`. El filtrado se hace automáticamente en un `QuerySet` base que filtra por `negocio=request.user.negocio`. Ningún endpoint devuelve datos de otro negocio.

---

## API — Endpoints MVP

### Autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/auth/registro/` | Crear negocio + usuario dueño |
| POST | `/api/auth/login/` | Devuelve `access` y `refresh` JWT |
| POST | `/api/auth/token/refresh/` | Renovar access token |
| GET/PATCH | `/api/auth/perfil/` | Ver y editar datos del usuario autenticado |
| POST | `/api/auth/cambiar-password/` | Cambiar contraseña |

### Negocio (tenant)

| Método | Endpoint | Descripción |
|---|---|---|
| GET/PATCH | `/api/negocio/` | Ver y editar datos del negocio (seed_color, theme_mode, nombre, tipo) |

### Productos / Insumos

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/productos/` | Lista con filtro por categoría, búsqueda por nombre |
| POST | `/api/productos/` | Crear producto |
| GET/PATCH/DELETE | `/api/productos/{id}/` | Detalle, editar, archivar (soft delete) |
| POST | `/api/productos/{id}/movimiento/` | Registrar entrada o salida |
| GET | `/api/productos/{id}/movimientos/` | Historial de movimientos |

### Proveedores

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/proveedores/` | Lista con búsqueda por nombre |
| POST | `/api/proveedores/` | Crear proveedor |
| GET/PATCH/DELETE | `/api/proveedores/{id}/` | Detalle, editar, archivar |

### Dashboard

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/dashboard/` | Resumen del día: total ventas, alertas de stock, últimos movimientos |

### Chat IA

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/chat/mensaje/` | Envía texto al LLM, devuelve propuesta estructurada |
| POST | `/api/chat/audio/` | Sube audio → Whisper transcribe → devuelve propuesta |
| POST | `/api/chat/foto/` | Sube imagen de factura → Claude Haiku extrae datos → devuelve propuesta |
| POST | `/api/chat/confirmar/` | El usuario aprueba una propuesta → se escribe a la BD |

---

## Flujo del Chat IA

```
Usuario (audio/foto/texto)
        ↓
  /api/chat/audio|foto|mensaje
        ↓
  [Whisper] si es audio → texto
  [Claude Haiku] interpreta + extrae datos estructurados
        ↓
  Devuelve propuesta JSON al Flutter
        ↓
  Usuario confirma en la app
        ↓
  /api/chat/confirmar/
        ↓
  Django escribe en PostgreSQL
```

### Formato de propuesta del LLM

```json
{
  "accion": "registrar_movimiento",
  "datos": {
    "producto": "Arroz",
    "tipo": "entrada",
    "cantidad": 10,
    "unidad": "kg",
    "proveedor": "Distribuidora El Campo"
  },
  "resumen": "Entrada de 10 kg de arroz del proveedor Distribuidora El Campo."
}
```

---

## Arquitectura del proyecto Django

```
backend/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── autenticacion/      # custom User, JWT, registro, perfil
│   ├── negocios/           # modelo Negocio, endpoint de configuración
│   ├── inventario/         # Producto, Movimiento
│   ├── proveedores/        # Proveedor
│   ├── dashboard/          # endpoint de resumen
│   └── chat/               # integración Anthropic + Whisper
├── requirements.txt
├── Procfile                # gunicorn config/wsgi:application
└── .env.example
```

---

## Variables de entorno

```env
SECRET_KEY=
DEBUG=False
DATABASE_URL=postgres://...
ALLOWED_HOSTS=.railway.app
ANTHROPIC_API_KEY=
OPENAI_API_KEY=                # solo para Whisper
CORS_ALLOWED_ORIGINS=https://...
```

---

## Plan de ejecución

### Paso 1: Setup del proyecto

- Crear proyecto Django limpio en `/Backend`.
- Instalar dependencias en `requirements.txt`.
- Configurar `settings.py` con `python-decouple` para leer `.env`.
- Custom User model con email como username desde el inicio (no se puede cambiar después).
- Configurar `django-cors-headers`.

### Paso 2: Modelo de datos y migraciones

- Crear todas las apps (`autenticacion`, `negocios`, `inventario`, `proveedores`).
- Definir modelos con UUID como PK y FK a `Negocio` en cada modelo de negocio.
- Correr migraciones iniciales.

### Paso 3: Autenticación

- Endpoints de registro (crea `Negocio` + `Usuario` en una transacción atómica), login, refresh, perfil y cambio de contraseña.
- Validar JWT en todos los endpoints protegidos.

### Paso 4: CRUD principal

En este orden:

1. Negocio (GET/PATCH)
2. Proveedores (CRUD)
3. Productos (CRUD + movimientos)
4. Dashboard

### Paso 5: Chat IA

- Endpoint `/chat/mensaje/` con llamada a `anthropic` SDK usando `claude-haiku-4-5`.
- System prompt especializado en gestión de inventario gastronómico (español ecuatoriano).
- Endpoint `/chat/audio/` con llamada a Whisper antes de pasar al LLM.
- Endpoint `/chat/foto/` con visión de Claude Haiku para extraer datos de facturas.
- Endpoint `/chat/confirmar/` que escribe a la BD según la acción propuesta.

### Paso 6: Deploy en Railway

- Crear `Procfile` con Gunicorn.
- Configurar variables de entorno en Railway.
- Conectar PostgreSQL de Railway.
- Correr migraciones en Railway con `railway run python manage.py migrate`.

---

## Conexión con el Frontend Flutter

El frontend ya tiene `core/api/api_client.dart` con Dio e interceptor JWT listo. Al conectar:

1. Definir `BASE_URL` apuntando al backend Railway (o IP local en desarrollo).
2. Reemplazar mock data de cada feature con llamadas reales al cliente HTTP.
3. Los providers de Riverpod manejan el estado; los widgets no cambian.

---

## Lo que NO se hace en esta fase

- Roles múltiples (empleados con permisos distintos).
- Notificaciones push.
- Reportes exportables (PDF/Excel).
- Multiidioma.
- Tests automatizados extensivos (sí validaciones básicas de endpoints).

---

## Criterios de cierre del MVP backend

- Todos los endpoints responden con status codes correctos.
- JWT funciona: token expira, refresh renueva, endpoints protegidos rechazan sin token.
- Multitenancy: un usuario no puede ver datos de otro negocio.
- Chat IA completa el flujo: texto → propuesta → confirmar → dato guardado en BD.
- Deploy estable en Railway con PostgreSQL conectado.
- El frontend Flutter conecta al backend sin errores (reemplazando los mocks de al menos login, productos y proveedores).
