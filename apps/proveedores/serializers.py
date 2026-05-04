from rest_framework import serializers
from .models import Proveedor


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['id', 'nombre', 'contacto', 'telefono', 'email', 'direccion', 'activo']
        read_only_fields = ['id']
