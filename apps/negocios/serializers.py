from rest_framework import serializers
from .models import Negocio


class NegocioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Negocio
        fields = ['id', 'nombre', 'tipo', 'seed_color', 'theme_mode']
        read_only_fields = ['id']
