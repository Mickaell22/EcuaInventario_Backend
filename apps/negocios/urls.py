from django.urls import path
from .views import NegocioView

urlpatterns = [
    path('', NegocioView.as_view(), name='negocio-detalle'),
]
