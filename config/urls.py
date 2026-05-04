from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.autenticacion.urls')),
    # path('api/negocio/', include('apps.negocios.urls')),
    # path('api/productos/', include('apps.inventario.urls')),
    # path('api/proveedores/', include('apps.proveedores.urls')),
    # path('api/ventas/', include('apps.ventas.urls')),
    # path('api/dashboard/', include('apps.dashboard.urls')),
    # path('api/chat/', include('apps.chat.urls')),
]
