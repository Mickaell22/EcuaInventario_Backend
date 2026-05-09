from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class ChatMensajeView(APIView):
    def post(self, request):
        texto = request.data.get('mensaje', '').strip()
        if not texto:
            return Response({'error': 'El campo "mensaje" es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            propuesta = services.procesar_mensaje(texto, request.user.negocio)
            return Response(services._format_for_flutter(propuesta))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatAudioView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        audio = request.FILES.get('audio')
        if not audio:
            return Response({'error': 'Se requiere un archivo de audio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            texto = services.transcribir_audio(audio)
            propuesta = services.procesar_mensaje(texto, request.user.negocio)
            respuesta = services._format_for_flutter(propuesta)
            respuesta['transcripcion'] = texto
            return Response(respuesta)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatFotoView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        foto = request.FILES.get('foto')
        if not foto:
            return Response({'error': 'Se requiere una imagen.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            propuesta = services.procesar_foto(foto, request.user.negocio)
            return Response(services._format_for_flutter(propuesta))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatConfirmarView(APIView):
    def post(self, request):
        accion = request.data.get('accion')
        datos = request.data.get('datos', {})
        if not accion:
            return Response({'error': 'Se requiere el campo "accion".'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resultado = services.confirmar_accion(
                {'accion': accion, 'datos': datos},
                request.user.negocio,
                request.user,
            )
            return Response(resultado, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
