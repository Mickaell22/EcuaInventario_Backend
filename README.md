# EcuaInventario — Backend

API REST para plataforma SaaS gastronómica. Gestión de inventario, proveedores, ventas y chat IA para pequeños negocios de comida en Ecuador.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.x-A30000?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Deploy-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)

---

## Descripción

Backend multitenancy para negocios de comida (restaurantes, cevicherías, etc.). Cada negocio tiene sus datos completamente aislados. El diferenciador es el **chat IA** que interpreta texto, audio y fotos de facturas para registrar movimientos de inventario — nunca escribe a la BD sin confirmación del usuario.

---

## Módulos

| Módulo | Descripción |
|--------|-------------|
| **Autenticación** | Registro, login JWT, refresh token, perfil, cambio de contraseña |
| **Negocios** | Configuración del negocio (tenant): nombre, tipo, tema visual |
| **Inventario** | CRUD de productos/insumos, movimientos de entrada/salida, alertas de stock bajo |
| **Proveedores** | CRUD de proveedores por negocio |
| **Ventas** | Registro de ventas con detalle de productos |
| **Dashboard** | Resumen del día: ventas, stock crítico, últimos movimientos |
| **Chat IA** | Texto → DeepSeek · Audio → Whisper · Foto de factura → Claude Haiku |

---

## Chat IA — Flujo

```
Usuario envía texto / audio / foto de factura
        ↓
IA interpreta y genera una propuesta estructurada
        ↓
Usuario confirma o descarta
        ↓
Solo si confirma → se escribe a la BD
```

Endpoints:
- `POST /chat/mensaje/` — texto libre → propuesta de movimiento
- `POST /chat/audio/` — audio (voz) → transcripción Whisper → propuesta
- `POST /chat/foto/` — foto de factura → Claude Haiku → propuesta
- `POST /chat/confirmar/` — aplica la propuesta aprobada a la BD

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Framework | Django 5 + Django REST Framework |
| Base de datos | PostgreSQL 16 |
| Autenticación | JWT — `djangorestframework-simplejwt` |
| IA Chat / Visión | Claude Haiku (`anthropic` SDK) |
| IA Audio | Whisper (`openai` SDK) |
| IA Procesamiento | DeepSeek Flash |
| Variables de entorno | `python-decouple` |
| CORS | `django-cors-headers` |
| Deploy | Railway + Gunicorn |

---

## Estructura del proyecto

```
backend/
├── config/
│   ├── settings.py       # Configuración principal
│   ├── urls.py           # Router raíz
│   └── wsgi.py
├── apps/
│   ├── autenticacion/    # JWT auth + modelo Usuario custom
│   ├── negocios/         # Modelo Negocio (tenant) + seed
│   ├── inventario/       # Productos, movimientos, stock
│   ├── proveedores/      # CRUD proveedores
│   ├── ventas/           # Registro de ventas
│   ├── dashboard/        # Resumen del día
│   ├── chat/             # Chat IA (texto / audio / visión)
│   └── core/             # Mixins y utilidades compartidas
├── manage.py
├── Procfile              # Para Railway
└── requirements.txt
```

---

## Variables de entorno

Crea un archivo `.env` basado en `.env.example`:

```env
SECRET_KEY=cambia-esto-por-una-clave-segura
DEBUG=True
DATABASE_URL=postgres://usuario:password@localhost:5432/ecuainventario
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000

# APIs de IA (opcionales en desarrollo)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
```

---

## Instalación local

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Aplicar migraciones
python manage.py migrate

# (Opcional) Cargar datos de prueba
python manage.py seed

# Iniciar servidor
python manage.py runserver
```

API disponible en `http://localhost:8000`
Documentación en `http://localhost:8000/api/schema/swagger-ui/`

---

## Deploy en Railway

1. Crea un nuevo proyecto en [Railway](https://railway.app)
2. Agrega un servicio **PostgreSQL**
3. Conecta este repositorio como servicio web
4. Agrega las variables de entorno (Settings → Variables)
5. Railway usa el `Procfile` para iniciar con Gunicorn

---

## Frontend

Este backend es consumido por la app móvil **Flutter** (repositorio separado).
El frontend reemplaza los mocks con llamadas reales a esta API en producción.
