from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('api/auth/', include('apps.autenticacion.urls')),
    path('api/negocios/', include('apps.negocios.urls')),
    path('api/inventario/', include('apps.inventario.urls')),
    path('api/proveedores/', include('apps.proveedores.urls')),
    path('api/ventas/', include('apps.ventas.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/chat/', include('apps.chat.urls')),
]

if settings.DEBUG:
    urlpatterns = [path('admin/', admin.site.urls)] + urlpatterns
