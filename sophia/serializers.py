from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    User,
    Aluno,
    Professor,
    Turma,
    Nota,
    Mensalidade,
    Escola,
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adiciona informações extras no token JWT"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Adiciona claims customizados
        token['role'] = user.role
        token['nome'] = user.get_full_name()
        token['foto'] = user.foto

        # Adiciona escolas do usuário
        escolas = user.escolas.values_list('escola_id', flat=True)
        token['escolas'] = list(escolas)

        return token


class UserSerializer(serializers.ModelSerializer):
    """Serializer para leitura de usuários"""
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
    """Serializer para criação de usuários"""
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
            raise serializers.ValidationError({
                "password": "As senhas não coincidem"
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        return user


class AlunoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem de alunos"""
    nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    foto = serializers.URLField(source='usuario.foto', read_only=True)
    turma_nome = serializers.CharField(source='turma_atual.nome', read_only=True)
    turno = serializers.CharField(source='turma_atual.turno', read_only=True)
    responsaveis = serializers.SerializerMethodField()

    class Meta:
        model = Aluno
        fields = [
            'id', 'nome', 'matricula', 'foto', 'turma_atual',
            'turma_nome', 'turno', 'status', 'responsaveis'
        ]

    def get_responsaveis(self, obj):
        return [{
            'id': str(ar.responsavel.id),
            'nome': ar.responsavel.usuario.get_full_name(),
            'parentesco': ar.responsavel.parentesco,
            'telefone': ar.responsavel.usuario.telefone,
            'email': ar.responsavel.usuario.email,
            'responsavel_financeiro': ar.responsavel_financeiro
        } for ar in obj.responsaveis.select_related('responsavel__usuario').all()]


class AlunoSerializer(serializers.ModelSerializer):
    """Serializer completo para alunos"""
    usuario = UserSerializer(read_only=True)

    class Meta:
        model = Aluno
        fields = '__all__'


class ProfessorListSerializer(serializers.ModelSerializer):
    """Serializer para listagem de professores"""
    nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)
    disciplinas = serializers.SerializerMethodField()
    turmas = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = [
            'id', 'nome', 'email', 'formacao', 'especializacao',
            'disciplinas', 'turmas', 'carga_horaria', 'status'
        ]

    def get_disciplinas(self, obj):
        return list(obj.usuario.disciplinas_lecionadas.values_list(
            'disciplina__nome', flat=True
        ).distinct())

    def get_turmas(self, obj):
        return list(obj.usuario.disciplinas_lecionadas.values_list(
            'turma__nome', flat=True
        ).distinct())


class NotaSerializer(serializers.ModelSerializer):
    """Serializer para notas"""
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    disciplina_nome = serializers.CharField(source='turma_disciplina.disciplina.nome', read_only=True)
    periodo_nome = serializers.CharField(source='periodo.nome', read_only=True)

    class Meta:
        model = Nota
        fields = '__all__'
        read_only_fields = ['lancado_por', 'lancado_em']

    def create(self, validated_data):
        validated_data['lancado_por'] = self.context['request'].user
        return super().create(validated_data)


class MensalidadeSerializer(serializers.ModelSerializer):
    """Serializer para mensalidades"""
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    responsavel_nome = serializers.CharField(source='responsavel_financeiro.usuario.get_full_name', read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)

    class Meta:
        model = Mensalidade
        fields = '__all__'

