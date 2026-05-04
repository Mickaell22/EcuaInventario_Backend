from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NegocioSerializer


class NegocioView(APIView):
    def get(self, request):
        serializer = NegocioSerializer(request.user.negocio)
        return Response(serializer.data)

    def patch(self, request):
        serializer = NegocioSerializer(
            request.user.negocio, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
