from django.urls import path
from .views import ChatAudioView, ChatConfirmarView, ChatFotoView, ChatMensajeView

urlpatterns = [
    path('mensaje/', ChatMensajeView.as_view(), name='chat-mensaje'),
    path('audio/', ChatAudioView.as_view(), name='chat-audio'),
    path('foto/', ChatFotoView.as_view(), name='chat-foto'),
    path('confirmar/', ChatConfirmarView.as_view(), name='chat-confirmar'),
]
