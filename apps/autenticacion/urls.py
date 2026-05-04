from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import CambiarPasswordView, LoginView, PerfilView, RegistroView

urlpatterns = [
    path('registro/', RegistroView.as_view(), name='auth-registro'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('perfil/', PerfilView.as_view(), name='auth-perfil'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='auth-cambiar-password'),
]
