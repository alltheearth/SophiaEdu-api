from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password

from .models import (
    User
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['nome'] = user.get_full_name()
        token['foto'] = user.foto

        # Buscar escolas do usuário
        vinculos = user.escolas.filter(ativo=True)
        escolas = [
            {
                'id': str(v.escola_id),
                'nome': v.escola.nome,
                'logo': v.escola.logo,
                'role': v.role_na_escola
            }
            for v in vinculos.select_related('escola')
        ]

        token['escolas'] = escolas

        # Escola ativa (primeira ou última usada)
        if escolas:
            token['escola_ativa_id'] = escolas[0]['id']

        return token


class UserSerializer(serializers.ModelSerializer):
    nome_completo = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'nome_completo', 'role', 'cpf', 'telefone', 'foto',
            'ativo', 'email_verificado', 'primeiro_acesso',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'cpf', 'telefone'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "As senhas não coincidem"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

