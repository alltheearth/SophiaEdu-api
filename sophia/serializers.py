from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password

from .models import (
    User, Escola, EscolaUsuario, Professor, Aluno, Responsavel,
    AlunoResponsavel, AnoLetivo, Turma, Disciplina, TurmaDisciplina,
    PeriodoAvaliativo, Nota, Frequencia, Mensalidade, Aviso,
    Mensagem, AtividadeAgenda, Evento
)


# ============================================
# AUTENTICAÇÃO
# ============================================

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


# ============================================
# GESTÃO
# ============================================

class EscolaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escola
        fields = '__all__'


class EscolaUsuarioSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)

    class Meta:
        model = EscolaUsuario
        fields = '__all__'


# ============================================
# ACADÊMICO
# ============================================

class AnoLetivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnoLetivo
        fields = '__all__'


class DisciplinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disciplina
        fields = '__all__'


class TurmaSerializer(serializers.ModelSerializer):
    coordenador_nome = serializers.CharField(source='coordenador.get_full_name', read_only=True)
    professor_titular_nome = serializers.CharField(source='professor_titular.get_full_name', read_only=True)
    ano_letivo_ano = serializers.IntegerField(source='ano_letivo.ano', read_only=True)
    total_alunos = serializers.SerializerMethodField()

    class Meta:
        model = Turma
        fields = '__all__'

    def get_total_alunos(self, obj):
        return obj.alunos.count()


class TurmaDisciplinaSerializer(serializers.ModelSerializer):
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)
    professor_nome = serializers.CharField(source='professor.get_full_name', read_only=True)

    class Meta:
        model = TurmaDisciplina
        fields = '__all__'


class ProfessorListSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)
    foto = serializers.URLField(source='usuario.foto', read_only=True)
    disciplinas = serializers.SerializerMethodField()
    turmas = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = [
            'id', 'nome', 'email', 'foto', 'formacao', 'especializacao',
            'disciplinas', 'turmas', 'carga_horaria', 'turno', 'status'
        ]

    def get_disciplinas(self, obj):
        return list(obj.usuario.disciplinas_lecionadas.values_list(
            'disciplina__nome', flat=True
        ).distinct())

    def get_turmas(self, obj):
        return list(obj.usuario.disciplinas_lecionadas.values_list(
            'turma__nome', flat=True
        ).distinct())


class ProfessorSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)

    class Meta:
        model = Professor
        fields = '__all__'


class ResponsavelSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)
    alunos = serializers.SerializerMethodField()

    class Meta:
        model = Responsavel
        fields = '__all__'

    def get_alunos(self, obj):
        # ✅ CORRETO: Acessar através do modelo intermediário AlunoResponsavel
        vinculos = AlunoResponsavel.objects.filter(responsavel=obj).select_related('aluno__usuario')
        return [{
            'id': str(vinculo.aluno.id),
            'nome': vinculo.aluno.usuario.get_full_name(),
            'matricula': vinculo.aluno.matricula,
            'responsavel_financeiro': vinculo.responsavel_financeiro
        } for vinculo in vinculos]


class AlunoListSerializer(serializers.ModelSerializer):
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
        # ✅ CORRETO: Acessar através do modelo intermediário AlunoResponsavel
        vinculos = AlunoResponsavel.objects.filter(aluno=obj).select_related('responsavel__usuario')
        return [{
            'id': str(vinculo.responsavel.id),
            'nome': vinculo.responsavel.usuario.get_full_name(),
            'parentesco': vinculo.responsavel.parentesco,
            'telefone': vinculo.responsavel.usuario.telefone,
            'email': vinculo.responsavel.usuario.email,
            'responsavel_financeiro': vinculo.responsavel_financeiro
        } for vinculo in vinculos]


class AlunoSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)
    turma_nome = serializers.CharField(source='turma_atual.nome', read_only=True)

    class Meta:
        model = Aluno
        fields = '__all__'


# ============================================
# NOTAS E FREQUÊNCIA
# ============================================

class PeriodoAvaliativoSerializer(serializers.ModelSerializer):
    ano_letivo_ano = serializers.IntegerField(source='ano_letivo.ano', read_only=True)

    class Meta:
        model = PeriodoAvaliativo
        fields = '__all__'


class NotaSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    disciplina_nome = serializers.CharField(source='turma_disciplina.disciplina.nome', read_only=True)
    periodo_nome = serializers.CharField(source='periodo.nome', read_only=True)
    lancado_por_nome = serializers.CharField(source='lancado_por.get_full_name', read_only=True)

    class Meta:
        model = Nota
        fields = '__all__'
        read_only_fields = ['lancado_por', 'lancado_em']

    def create(self, validated_data):
        validated_data['lancado_por'] = self.context['request'].user
        return super().create(validated_data)


class FrequenciaSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    disciplina_nome = serializers.CharField(source='turma_disciplina.disciplina.nome', read_only=True)
    lancado_por_nome = serializers.CharField(source='lancado_por.get_full_name', read_only=True)

    class Meta:
        model = Frequencia
        fields = '__all__'
        read_only_fields = ['lancado_por', 'lancado_em']

    def create(self, validated_data):
        validated_data['lancado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================
# FINANCEIRO
# ============================================

class MensalidadeSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.usuario.get_full_name', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    responsavel_nome = serializers.CharField(source='responsavel_financeiro.usuario.get_full_name', read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Mensalidade
        fields = '__all__'


# ============================================
# COMUNICAÇÃO
# ============================================

class AvisoSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source='autor.get_full_name', read_only=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)
    turmas_nomes = serializers.SerializerMethodField()

    class Meta:
        model = Aviso
        fields = '__all__'
        read_only_fields = ['autor', 'criado_em']

    def get_turmas_nomes(self, obj):
        return list(obj.turmas.values_list('nome', flat=True))


class MensagemSerializer(serializers.ModelSerializer):
    remetente_nome = serializers.CharField(source='remetente.get_full_name', read_only=True)
    destinatario_nome = serializers.CharField(source='destinatario.get_full_name', read_only=True)

    class Meta:
        model = Mensagem
        fields = '__all__'
        read_only_fields = ['remetente', 'enviada_em']

    def create(self, validated_data):
        validated_data['remetente'] = self.context['request'].user
        return super().create(validated_data)


# ============================================
# AGENDA E EVENTOS
# ============================================

class AtividadeAgendaSerializer(serializers.ModelSerializer):
    professor_nome = serializers.CharField(source='professor.get_full_name', read_only=True)
    turma_nome = serializers.CharField(source='turma_disciplina.turma.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='turma_disciplina.disciplina.nome', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = AtividadeAgenda
        fields = '__all__'
        read_only_fields = ['professor', 'criada_em']


class EventoSerializer(serializers.ModelSerializer):
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)
    responsavel_nome = serializers.CharField(source='responsavel.get_full_name', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    turmas_nomes = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = '__all__'

    def get_turmas_nomes(self, obj):
        return list(obj.turmas.values_list('nome', flat=True))


# ============================================
# DASHBOARD
# ============================================

class DashboardSerializer(serializers.Serializer):
    total_alunos = serializers.IntegerField()
    total_professores = serializers.IntegerField()
    total_turmas = serializers.IntegerField()
    mensalidades_pendentes = serializers.DictField()
    mensalidades_atrasadas = serializers.DictField()