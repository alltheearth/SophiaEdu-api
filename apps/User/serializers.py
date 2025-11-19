from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .models import User
from ..Schools.models import EscolaUsuario


class UserSerializer(serializers.ModelSerializer):
    nome_completo = serializers.CharField(source='get_full_name', read_only=True)
    tem_escola_vinculada = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'nome_completo', 'role', 'cpf', 'telefone', 'foto',
            'ativo', 'email_verificado', 'primeiro_acesso',
            'tem_escola_vinculada', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    escola_id = serializers.UUIDField(write_only=True, required=False)
    role_na_escola = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'cpf', 'telefone',
            'escola_id', 'role_na_escola'
        ]

    def validate(self, attrs):
        # Validação de senha
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "As senhas não coincidem"})

        # Validação de escola obrigatória (exceto para SUPERUSER)
        role = attrs.get('role')
        escola_id = attrs.get('escola_id')

        if role != 'SUPERUSER' and not escola_id:
            raise serializers.ValidationError({
                "escola_id": "Usuários que não são SUPERUSER devem estar vinculados a uma escola"
            })

        # Se escola_id foi fornecida, verifica se existe
        if escola_id:
            from ..Schools.models import Escola
            try:
                escola = Escola.objects.get(id=escola_id, ativo=True)
                attrs['_escola'] = escola
            except Escola.DoesNotExist:
                raise serializers.ValidationError({
                    "escola_id": "Escola não encontrada ou inativa"
                })

        # Define role_na_escola padrão se não fornecido
        if escola_id and not attrs.get('role_na_escola'):
            attrs['role_na_escola'] = role

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # Remove campos extras
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        escola_id = validated_data.pop('escola_id', None)
        role_na_escola = validated_data.pop('role_na_escola', None)
        escola = validated_data.pop('_escola', None)

        # Adiciona criador se disponível
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['criado_por'] = request.user

        # Cria usuário
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # Vincula à escola se não for SUPERUSER
        if escola and user.role != 'SUPERUSER':
            EscolaUsuario.objects.create(
                escola=escola,
                usuario=user,
                role_na_escola=role_na_escola
            )

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização de usuário"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'cpf',
            'telefone', 'foto'
        ]

    def validate(self, attrs):
        user = self.instance

        # Não permite que não-SUPERUSER fiquem sem escola
        if user.role != 'SUPERUSER':
            if not user.tem_escola_vinculada():
                raise serializers.ValidationError(
                    "Este usuário precisa estar vinculado a pelo menos uma escola"
                )

        return attrs