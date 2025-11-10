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


# sophia/serializers.py - ADICIONAR AO ARQUIVO EXISTENTE

from rest_framework import serializers
from .models import (
    CanalComunicacao, ParticipanteCanal, MensagemCanal,
    AnexoMensagem, ResponsavelConversa, NotificacaoComunicacao,
    AuditoriaConversa, Visualizacao
)


# ============================================
# COMUNICAÇÃO - SERIALIZERS
# ============================================

class ParticipanteCanalSerializer(serializers.ModelSerializer):
    """Serializer para participantes do canal"""
    nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)
    foto = serializers.URLField(source='usuario.foto', read_only=True)
    role = serializers.CharField(source='usuario.role', read_only=True)
    papel_display = serializers.CharField(source='get_papel_display', read_only=True)

    class Meta:
        model = ParticipanteCanal
        fields = [
            'id', 'usuario', 'nome', 'email', 'foto', 'role',
            'papel', 'papel_display', 'ativo', 'pode_enviar',
            'notificar', 'adicionado_em', 'ultima_visualizacao'
        ]
        read_only_fields = ['adicionado_em', 'ultima_visualizacao']


class AnexoMensagemSerializer(serializers.ModelSerializer):
    """Serializer para anexos"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    tamanho_mb = serializers.SerializerMethodField()

    class Meta:
        model = AnexoMensagem
        fields = [
            'id', 'tipo', 'tipo_display', 'nome_arquivo', 'url',
            'tamanho', 'tamanho_mb', 'mime_type', 'e_trabalho',
            'atividade', 'nota_trabalho', 'feedback_professor',
            'enviado_em', 'downloads'
        ]
        read_only_fields = ['enviado_em', 'downloads']

    def get_tamanho_mb(self, obj):
        """Retorna tamanho em MB"""
        return round(obj.tamanho / (1024 * 1024), 2)


class VisualizacaoSerializer(serializers.ModelSerializer):
    """Serializer para visualizações"""
    nome_usuario = serializers.CharField(source='usuario.get_full_name', read_only=True)
    foto_usuario = serializers.URLField(source='usuario.foto', read_only=True)

    class Meta:
        model = Visualizacao
        fields = ['id', 'usuario', 'nome_usuario', 'foto_usuario', 'visualizada_em']


class MensagemCanalSerializer(serializers.ModelSerializer):
    """Serializer para mensagens"""
    remetente_nome = serializers.CharField(source='remetente.get_full_name', read_only=True)
    remetente_foto = serializers.URLField(source='remetente.foto', read_only=True)
    remetente_role = serializers.CharField(source='remetente.role', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)

    anexos = AnexoMensagemSerializer(many=True, read_only=True)
    respostas = serializers.SerializerMethodField()
    visualizacoes_detalhadas = VisualizacaoSerializer(many=True, read_only=True)
    total_visualizacoes = serializers.IntegerField(source='visualizacoes', read_only=True)

    # Info da mensagem respondida
    respondendo_a_info = serializers.SerializerMethodField()

    class Meta:
        model = MensagemCanal
        fields = [
            'id', 'canal', 'remetente', 'remetente_nome', 'remetente_foto',
            'remetente_role', 'tipo', 'tipo_display', 'conteudo',
            'prioridade', 'prioridade_display', 'respondendo_a',
            'respondendo_a_info', 'anexos', 'respostas', 'editada',
            'editada_em', 'excluida', 'lida', 'lida_em',
            'visualizacoes_detalhadas', 'total_visualizacoes',
            'requer_confirmacao', 'enviada_em'
        ]
        read_only_fields = ['remetente', 'enviada_em', 'editada', 'editada_em']

    def get_respostas(self, obj):
        """Retorna respostas (threads)"""
        respostas = obj.respostas.filter(excluida=False).select_related('remetente')[:10]
        return MensagemCanalSerializer(respostas, many=True, context=self.context).data

    def get_respondendo_a_info(self, obj):
        """Informações da mensagem respondida"""
        if obj.respondendo_a:
            return {
                'id': str(obj.respondendo_a.id),
                'remetente': obj.respondendo_a.remetente.get_full_name(),
                'conteudo': obj.respondendo_a.conteudo[:100]
            }
        return None


class ResponsavelConversaSerializer(serializers.ModelSerializer):
    """Serializer para responsáveis de conversa"""
    responsavel_original_nome = serializers.CharField(source='responsavel_original.get_full_name', read_only=True)
    assumida_por_nome = serializers.CharField(source='assumida_por.get_full_name', read_only=True)
    esta_atrasado = serializers.BooleanField(read_only=True)
    tempo_decorrido_horas = serializers.SerializerMethodField()

    class Meta:
        model = ResponsavelConversa
        fields = [
            'id', 'canal', 'responsavel_original', 'responsavel_original_nome',
            'assumida_por', 'assumida_por_nome', 'assumida_em',
            'motivo_assuncao', 'ativo', 'devolvida', 'devolvida_em',
            'prazo_resposta', 'alertado', 'atrasado', 'esta_atrasado',
            'tempo_decorrido_horas', 'criado_em', 'atualizado_em'
        ]

    def get_tempo_decorrido_horas(self, obj):
        """Tempo decorrido desde última mensagem"""
        if not obj.canal.ultima_mensagem_em:
            return 0
        from django.utils import timezone
        delta = timezone.now() - obj.canal.ultima_mensagem_em
        return round(delta.total_seconds() / 3600, 1)


class CanalComunicacaoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para lista de canais"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_participantes = serializers.SerializerMethodField()
    mensagens_nao_lidas = serializers.SerializerMethodField()
    ultima_mensagem = serializers.SerializerMethodField()
    meu_papel = serializers.SerializerMethodField()

    class Meta:
        model = CanalComunicacao
        fields = [
            'id', 'tipo', 'tipo_display', 'nome', 'descricao',
            'status', 'status_display', 'fixado', 'total_participantes',
            'mensagens_nao_lidas', 'ultima_mensagem', 'ultima_mensagem_em',
            'meu_papel', 'criado_em'
        ]

    def get_total_participantes(self, obj):
        return obj.participantes.filter(ativo=True).count()

    def get_mensagens_nao_lidas(self, obj):
        usuario = self.context['request'].user
        return obj.obter_nao_lidas(usuario)

    def get_ultima_mensagem(self, obj):
        """Última mensagem do canal"""
        ultima = obj.mensagens.filter(excluida=False).select_related('remetente').last()
        if ultima:
            return {
                'id': str(ultima.id),
                'remetente': ultima.remetente.get_full_name(),
                'conteudo': ultima.conteudo[:100],
                'enviada_em': ultima.enviada_em
            }
        return None

    def get_meu_papel(self, obj):
        """Papel do usuário atual no canal"""
        usuario = self.context['request'].user
        participante = obj.participantes.filter(usuario=usuario).first()
        return participante.get_papel_display() if participante else None


class CanalComunicacaoSerializer(serializers.ModelSerializer):
    """Serializer completo para canal"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    criado_por_nome = serializers.CharField(source='criado_por.get_full_name', read_only=True)
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)

    participantes = ParticipanteCanalSerializer(many=True, read_only=True)
    responsaveis = ResponsavelConversaSerializer(many=True, read_only=True)
    mensagens_recentes = serializers.SerializerMethodField()
    estatisticas = serializers.SerializerMethodField()

    class Meta:
        model = CanalComunicacao
        fields = [
            'id', 'escola', 'tipo', 'tipo_display', 'nome', 'descricao',
            'turma', 'turma_nome', 'disciplina', 'disciplina_nome',
            'criado_por', 'criado_por_nome', 'status', 'status_display',
            'visivel_para_gestao', 'visivel_para_coordenacao',
            'permite_anexos', 'permite_entrega_trabalhos',
            'fixado', 'participantes', 'responsaveis',
            'mensagens_recentes', 'estatisticas',
            'criado_em', 'atualizado_em', 'ultima_mensagem_em'
        ]
        read_only_fields = ['criado_por', 'criado_em', 'atualizado_em']

    def get_mensagens_recentes(self, obj):
        """Últimas 50 mensagens"""
        mensagens = obj.mensagens.filter(excluida=False).select_related('remetente').order_by('-enviada_em')[:50]
        return MensagemCanalSerializer(mensagens, many=True, context=self.context).data

    def get_estatisticas(self, obj):
        """Estatísticas do canal"""
        return {
            'total_mensagens': obj.mensagens.filter(excluida=False).count(),
            'total_participantes': obj.participantes.filter(ativo=True).count(),
            'total_anexos': AnexoMensagem.objects.filter(mensagem__canal=obj).count(),
            'trabalhos_entregues': AnexoMensagem.objects.filter(
                mensagem__canal=obj,
                e_trabalho=True
            ).count()
        }


class NotificacaoComunicacaoSerializer(serializers.ModelSerializer):
    """Serializer para notificações"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    canal_nome = serializers.CharField(source='canal.nome', read_only=True)

    class Meta:
        model = NotificacaoComunicacao
        fields = [
            'id', 'tipo', 'tipo_display', 'canal', 'canal_nome',
            'mensagem', 'titulo', 'conteudo', 'lida', 'lida_em',
            'criada_em'
        ]
        read_only_fields = ['criada_em']


class AuditoriaConversaSerializer(serializers.ModelSerializer):
    """Serializer para auditoria"""
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    acao_display = serializers.CharField(source='get_acao_display', read_only=True)
    canal_nome = serializers.CharField(source='canal.nome', read_only=True)

    class Meta:
        model = AuditoriaConversa
        fields = [
            'id', 'usuario', 'usuario_nome', 'acao', 'acao_display',
            'canal', 'canal_nome', 'mensagem', 'detalhes',
            'ip_address', 'criado_em'
        ]
        read_only_fields = ['criado_em']


# ============================================
# SERIALIZERS PARA CRIAÇÃO
# ============================================

class CriarCanalSerializer(serializers.Serializer):
    """Serializer para criar canal"""
    tipo = serializers.ChoiceField(choices=CanalComunicacao.TIPO_CHOICES)
    nome = serializers.CharField(max_length=200, required=False)
    descricao = serializers.CharField(required=False, allow_blank=True)
    turma = serializers.UUIDField(required=False, allow_null=True)
    disciplina = serializers.UUIDField(required=False, allow_null=True)
    participantes_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    permite_anexos = serializers.BooleanField(default=True)
    permite_entrega_trabalhos = serializers.BooleanField(default=False)
    visivel_para_coordenacao = serializers.BooleanField(default=True)


class EnviarMensagemSerializer(serializers.Serializer):
    """Serializer para enviar mensagem"""
    conteudo = serializers.CharField()
    tipo = serializers.ChoiceField(
        choices=MensagemCanal.TIPO_CHOICES,
        default='TEXTO'
    )
    prioridade = serializers.ChoiceField(
        choices=MensagemCanal.PRIORIDADE_CHOICES,
        default='NORMAL'
    )
    respondendo_a = serializers.UUIDField(required=False, allow_null=True)
    requer_confirmacao = serializers.BooleanField(default=False)
    anexos = serializers.ListField(
        child=serializers.JSONField(),
        required=False
    )


class AdicionarParticipantesSerializer(serializers.Serializer):
    """Serializer para adicionar participantes"""
    usuarios_ids = serializers.ListField(child=serializers.UUIDField())
    papel = serializers.ChoiceField(
        choices=ParticipanteCanal.PAPEL_CHOICES,
        default='MEMBRO'
    )
    notificar = serializers.BooleanField(default=True)


class AssumirConversaSerializer(serializers.Serializer):
    """Serializer para assumir conversa"""
    motivo = serializers.CharField(required=False, allow_blank=True)