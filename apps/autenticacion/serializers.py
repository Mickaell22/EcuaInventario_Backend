from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.negocios.models import Negocio
from apps.negocios.serializers import NegocioSerializer
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre', 'apellido']
        read_only_fields = ['id', 'email']


class RegistroSerializer(serializers.Serializer):
    # Negocio
    negocio_nombre = serializers.CharField(max_length=120)
    negocio_tipo = serializers.CharField(max_length=40, required=False, default='')
    negocio_seed_color = serializers.CharField(max_length=7, required=False, default='#1976D2')

    # Usuario
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    nombre = serializers.CharField(max_length=80)
    apellido = serializers.CharField(max_length=80, required=False, default='')

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este email ya está registrado.')
        return value

    def create(self, validated_data):
        with transaction.atomic():
            negocio = Negocio.objects.create(
                nombre=validated_data['negocio_nombre'],
                tipo=validated_data.get('negocio_tipo', ''),
                seed_color=validated_data.get('negocio_seed_color', '#1976D2'),
            )
            usuario = Usuario.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                nombre=validated_data['nombre'],
                apellido=validated_data.get('apellido', ''),
                negocio=negocio,
            )
        return usuario


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['usuario'] = UsuarioSerializer(self.user).data
        data['negocio'] = NegocioSerializer(self.user.negocio).data
        return data


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, min_length=8)

    def validate_password_actual(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password_nuevo'])
        user.save()
