from django.urls import path
from .views import NegocioView

urlpatterns = [
    path('mi-negocio/', NegocioView.as_view(), name='negocio-detalle'),
]
