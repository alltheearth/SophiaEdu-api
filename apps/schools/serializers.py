from rest_framework import serializers
from .models import (Escola, EscolaUsuario)
from ..User.serializers import UserSerializer

class EscolaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escola
        fields = '__all__'


class EscolaUsuarioSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)

    class Meta:
        model = EscolaUsuario
        fields = '__all__'

