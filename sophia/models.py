from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import secrets
import string

# ============= CORE =============
class User(AbstractUser):
    """Usuário base do sistema com autenticação segura"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    role = models.CharField(max_length=20, choices=[
        ('SUPERUSER', 'Super Usuário'),
        ('GESTOR', 'Gestor'),
        ('COORDENADOR', 'Coordenador'),
        ('PROFESSOR', 'Professor'),
        ('RESPONSAVEL', 'Responsável'),
        ('ALUNO', 'Aluno'),
    ])

    # Dados pessoais
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    foto = models.URLField(blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True)

    # Controle de acesso
    ativo = models.BooleanField(default=True)
    email_verificado = models.BooleanField(default=False)
    primeiro_acesso = models.BooleanField(default=True)
    senha_temporaria = models.BooleanField(default=False)

    # Segurança
    tentativas_login_falhas = models.IntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    ultimo_login_ip = models.GenericIPAddressField(null=True, blank=True)

    # Auditoria
    criado_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_criados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='sophia_users',  # <-- ADICIONAR
        related_query_name='sophia_user',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='sophia_users',  # <-- ADICIONAR
        related_query_name='sophia_user',
        blank=True
    )

    class Meta:
        db_table = 'users'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def esta_bloqueado(self):
        """Verifica se usuário está bloqueado por tentativas"""
        if self.bloqueado_ate and self.bloqueado_ate > timezone.now():
            return True
        return False

    def registrar_tentativa_falha(self):
        """Registra tentativa de login falha"""
        self.tentativas_login_falhas += 1

        # Bloqueia após 5 tentativas por 30 minutos
        if self.tentativas_login_falhas >= 5:
            self.bloqueado_ate = timezone.now() + timezone.timedelta(minutes=30)

        self.save()

    def resetar_tentativas(self):
        """Reseta contador de tentativas após login bem-sucedido"""
        self.tentativas_login_falhas = 0
        self.bloqueado_ate = None
        self.save()

    def gerar_senha_temporaria(self):
        """Gera senha temporária segura de 12 caracteres"""
        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        senha = ''.join(secrets.choice(alphabet) for i in range(12))
        return senha

    def pode_criar_usuario(self, role_novo_usuario):
        """Verifica se usuário tem permissão para criar outro usuário"""
        hierarquia = {
            'SUPERUSER': ['GESTOR', 'COORDENADOR', 'PROFESSOR', 'RESPONSAVEL'],
            'GESTOR': ['COORDENADOR', 'PROFESSOR', 'RESPONSAVEL'],
            'COORDENADOR': ['PROFESSOR'],
            'PROFESSOR': [],
            'RESPONSAVEL': [],
            'ALUNO': []
        }

        return role_novo_usuario in hierarquia.get(self.role, [])


class TokenRedefinicaoSenha(models.Model):
    """Token para redefinição de senha"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens_senha')
    token = models.CharField(max_length=100, unique=True)
    usado = models.BooleanField(default=False)
    expira_em = models.DateTimeField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tokens_redefinicao_senha'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Token para {self.usuario.email}"

    @staticmethod
    def gerar_token():
        """Gera token único de 32 caracteres"""
        return secrets.token_urlsafe(32)

    def esta_valido(self):
        """Verifica se token ainda é válido"""
        if self.usado:
            return False
        if self.expira_em < timezone.now():
            return False
        return True

    def marcar_como_usado(self):
        """Marca token como usado"""
        self.usado = True
        self.save()


class HistoricoLogin(models.Model):
    """Histórico de logins para auditoria"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historico_logins')

    sucesso = models.BooleanField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    # Dados de localização (opcional)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historico_logins'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['usuario', '-timestamp']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        status = "✓" if self.sucesso else "✗"
        return f"{status} {self.usuario.email} - {self.timestamp}"


class SessaoUsuario(models.Model):
    """Sessões ativas dos usuários"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessoes')

    token = models.CharField(max_length=500, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    ativo = models.BooleanField(default=True)
    ultimo_acesso = models.DateTimeField(auto_now=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()

    class Meta:
        db_table = 'sessoes_usuarios'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Sessão de {self.usuario.email}"

    def esta_ativo(self):
        """Verifica se sessão ainda está ativa"""
        if not self.ativo:
            return False
        if self.expira_em < timezone.now():
            self.ativo = False
            self.save()
            return False
        return True

    def renovar(self):
        """Renova expiração da sessão"""
        self.expira_em = timezone.now() + timezone.timedelta(hours=8)
        self.save()


class Professor(models.Model):
    """Perfil de Professor"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='professor_profile')
    escola = models.ForeignKey('Escola', on_delete=models.CASCADE, related_name='professores')

    # Dados profissionais
    registro_profissional = models.CharField(max_length=50, blank=True)
    formacao = models.CharField(max_length=200)
    especializacao = models.CharField(max_length=200, blank=True)

    # Dados contratuais
    data_admissao = models.DateField()
    carga_horaria = models.IntegerField(default=40)
    turno = models.CharField(max_length=20, choices=[
        ('MATUTINO', 'Matutino'),
        ('VESPERTINO', 'Vespertino'),
        ('NOTURNO', 'Noturno'),
        ('INTEGRAL', 'Integral'),
    ])
    salario = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=[
        ('ATIVO', 'Ativo'),
        ('FERIAS', 'Férias'),
        ('LICENCA', 'Licença'),
        ('AFASTADO', 'Afastado'),
    ], default='ATIVO')

    class Meta:
        db_table = 'professores'
        verbose_name = 'Professor'
        verbose_name_plural = 'Professores'

    def __str__(self):
        return f"Prof. {self.usuario.get_full_name()}"


class Escola(models.Model):
    """Escola - Tenant principal"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, unique=True)

    # Contato
    endereco = models.TextField()
    telefone = models.CharField(max_length=15)
    email = models.EmailField()

    # Branding
    logo = models.URLField(blank=True, null=True)

    # Status
    ativo = models.BooleanField(default=True)
    plano = models.CharField(max_length=20, default='BASIC')

    # Configurações Asaas
    asaas_api_key = models.CharField(max_length=200, blank=True)
    asaas_wallet_id = models.CharField(max_length=100, blank=True)

    # Configurações de Segurança
    exigir_2fa = models.BooleanField(default=False)
    tempo_sessao_horas = models.IntegerField(default=8)
    max_tentativas_login = models.IntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'escolas'
        verbose_name = 'Escola'
        verbose_name_plural = 'Escolas'

    def __str__(self):
        return self.nome


class EscolaUsuario(models.Model):
    """Relacionamento Many-to-Many entre Escola e Usuário"""

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='usuarios_vinculados')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escolas')
    role_na_escola = models.CharField(max_length=20)

    ativo = models.BooleanField(default=True)
    data_vinculo = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'escola_usuarios'
        unique_together = ['escola', 'usuario']
        verbose_name = 'Vínculo Escola-Usuário'
        verbose_name_plural = 'Vínculos Escola-Usuário'

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.escola.nome}"

# ============= ACADÊMICO =============

class AnoLetivo(models.Model):
    """Ano letivo"""
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='anos_letivos')
    ano = models.IntegerField()
    data_inicio = models.DateField()
    data_fim = models.DateField()
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'anos_letivos'
        unique_together = ['escola', 'ano']


class Turma(models.Model):
    """Turmas/Classes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='turmas')
    ano_letivo = models.ForeignKey(AnoLetivo, on_delete=models.CASCADE, related_name='turmas')
    nome = models.CharField(max_length=100)  # Ex: "1º Ano A", "5º Ano B"
    serie = models.CharField(max_length=50)  # Ex: "1º Ano", "5º Ano"
    turno = models.CharField(max_length=20, choices=[
        ('MATUTINO', 'Matutino'),
        ('VESPERTINO', 'Vespertino'),
        ('NOTURNO', 'Noturno'),
        ('INTEGRAL', 'Integral'),
    ])
    capacidade_maxima = models.IntegerField(default=30)
    coordenador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='turmas_coordenadas')
    sala = models.CharField(max_length=20)
    professor_titular = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='turmas_tituladas'
    )

    class Meta:
        db_table = 'turmas'
        unique_together = ['escola', 'ano_letivo', 'nome']


class Disciplina(models.Model):
    """Matérias/Disciplinas"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='disciplinas')
    nome = models.CharField(max_length=100)  # Ex: "Matemática", "Português"
    codigo = models.CharField(max_length=20, blank=True)
    carga_horaria = models.IntegerField(help_text="Horas por semana")

    class Meta:
        db_table = 'disciplinas'


class TurmaDisciplina(models.Model):
    """Disciplinas de cada turma com professor"""
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='disciplinas')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    professor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='disciplinas_lecionadas')

    class Meta:
        db_table = 'turma_disciplinas'
        unique_together = ['turma', 'disciplina']


class Aluno(models.Model):
    """Alunos"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='aluno_profile')
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='alunos')
    matricula = models.CharField(max_length=50, unique=True)
    data_nascimento = models.DateField()
    turma_atual = models.ForeignKey(Turma, on_delete=models.SET_NULL, null=True, related_name='alunos')
    turno = models.CharField(max_length=20, choices=[
        ('MATUTINO', 'Matutino'),
        ('VESPERTINO', 'Vespertino'),
        ('NOTURNO', 'Noturno'),
        ('INTEGRAL', 'Integral'),
    ], blank=True)

    # Dados pessoais
    cpf = models.CharField(max_length=14, blank=True)
    rg = models.CharField(max_length=20, blank=True)
    endereco = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=[
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('TRANSFERIDO', 'Transferido'),
        ('CONCLUIDO', 'Concluído'),
    ], default='ATIVO')

    class Meta:
        db_table = 'alunos'

class Responsavel(models.Model):
    """Responsáveis/Pais"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='responsavel_profile')
    cpf = models.CharField(max_length=14, unique=True)
    parentesco = models.CharField(max_length=50)  # Pai, Mãe, Avô, Tio, etc
    profissao = models.CharField(max_length=100, blank=True)
    endereco = models.TextField(blank=True)

    class Meta:
        db_table = 'responsaveis'


class AlunoResponsavel(models.Model):
    """Relacionamento Aluno <-> Responsável (Many-to-Many)"""
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='responsaveis')
    responsavel = models.ForeignKey(Responsavel, on_delete=models.CASCADE, related_name='alunos')
    responsavel_financeiro = models.BooleanField(default=False)
    prioridade = models.IntegerField(default=1)  # 1 = principal, 2 = secundário

    class Meta:
        db_table = 'aluno_responsaveis'
        unique_together = ['aluno', 'responsavel']


# ============= NOTAS E FREQUÊNCIA =============

class PeriodoAvaliativo(models.Model):
    """Bimestre, Trimestre, Semestre"""
    ano_letivo = models.ForeignKey(AnoLetivo, on_delete=models.CASCADE, related_name='periodos')
    nome = models.CharField(max_length=50)  # "1º Bimestre", "2º Trimestre"
    data_inicio = models.DateField()
    data_fim = models.DateField()
    ordem = models.IntegerField()

    class Meta:
        db_table = 'periodos_avaliativos'
        ordering = ['ordem']


class Nota(models.Model):
    """Notas dos alunos"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='notas')
    turma_disciplina = models.ForeignKey(TurmaDisciplina, on_delete=models.CASCADE, related_name='notas')
    periodo = models.ForeignKey(PeriodoAvaliativo, on_delete=models.CASCADE, related_name='notas')

    nota = models.DecimalField(max_digits=4, decimal_places=2)
    tipo_avaliacao = models.CharField(max_length=50)  # Prova, Trabalho, Participação
    data_avaliacao = models.DateField()
    observacao = models.TextField(blank=True)

    lancado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    lancado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notas'


class Frequencia(models.Model):
    """Registro de presença"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='frequencias')
    turma_disciplina = models.ForeignKey(TurmaDisciplina, on_delete=models.CASCADE, related_name='frequencias')
    data = models.DateField()

    presente = models.BooleanField(default=True)
    justificativa = models.TextField(blank=True)

    lancado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    lancado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'frequencias'
        unique_together = ['aluno', 'turma_disciplina', 'data']


# ============= FINANCEIRO =============

class Mensalidade(models.Model):
    """Mensalidades"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='mensalidades')
    responsavel_financeiro = models.ForeignKey(Responsavel, on_delete=models.CASCADE, related_name='mensalidades')

    competencia = models.DateField()  # Mês/Ano de referência
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_final = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(max_length=20, choices=[
        ('BOLETO', 'Boleto'),
        ('PIX', 'PIX'),
        ('CARTAO', 'Cartão de Crédito'),
        ('DINHEIRO', 'Dinheiro'),
    ], blank=True)

    @property
    def dias_atraso(self):
        if self.status == 'ATRASADO' and not self.data_pagamento:
            from django.utils import timezone
            return (timezone.now().date() - self.data_vencimento).days
        return 0

    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=[
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('ATRASADO', 'Atrasado'),
        ('CANCELADO', 'Cancelado'),
    ], default='PENDENTE')

    # Integração Asaas
    asaas_payment_id = models.CharField(max_length=100, blank=True)
    boleto_url = models.URLField(blank=True)
    pix_qrcode = models.TextField(blank=True)

    class Meta:
        db_table = 'mensalidades'


# ============= COMUNICAÇÃO =============

class Aviso(models.Model):
    """Avisos e comunicados"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='avisos')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avisos_criados')

    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    anexos = models.JSONField(default=list, blank=True)  # Lista de URLs do Supabase Storage

    # Destinatários
    turmas = models.ManyToManyField(Turma, blank=True, related_name='avisos')
    enviar_para_todos = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'avisos'
        ordering = ['-criado_em']


class Mensagem(models.Model):
    """Chat/Mensagens diretas"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    remetente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensagens_enviadas')
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensagens_recebidas')

    mensagem = models.TextField()
    anexos = models.JSONField(default=list, blank=True)
    lida = models.BooleanField(default=False)

    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mensagens'
        ordering = ['enviada_em']


# ============= AGENDA =============

class AtividadeAgenda(models.Model):
    """Lição de casa, trabalhos, provas"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    turma_disciplina = models.ForeignKey(TurmaDisciplina, on_delete=models.CASCADE, related_name='atividades')
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='atividades_criadas')

    tipo = models.CharField(max_length=20, choices=[
        ('LICAO', 'Lição de Casa'),
        ('TRABALHO', 'Trabalho'),
        ('PROVA', 'Prova'),
        ('PROJETO', 'Projeto'),
    ])

    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    anexos = models.JSONField(default=list, blank=True)

    data_entrega = models.DateField()
    nota_maxima = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'atividades_agenda'

class Evento(models.Model):
    """Eventos do calendário escolar"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='eventos')

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=[
        ('REUNIAO', 'Reunião'),
        ('PROVA', 'Prova'),
        ('EVENTO', 'Evento'),
        ('FERIADO', 'Feriado'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('CULTURAL', 'Cultural'),
        ('ESPORTIVO', 'Esportivo'),
    ])

    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    local = models.CharField(max_length=200)
    descricao = models.TextField()

    turmas = models.ManyToManyField(Turma, blank=True, related_name='eventos')
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos_responsavel')
    participantes = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=[
        ('AGENDADO', 'Agendado'),
        ('CONFIRMADO', 'Confirmado'),
        ('CANCELADO', 'Cancelado'),
        ('REALIZADO', 'Realizado'),
    ], default='AGENDADO')

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'eventos'
        ordering = ['-data', '-hora_inicio']
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'

    def __str__(self):
        return f"{self.titulo} - {self.data}"


# sophia/models.py - ADICIONAR AO ARQUIVO EXISTENTE

from django.db import models
import uuid
from django.utils import timezone


# ============= SISTEMA DE COMUNICAÇÃO AVANÇADO =============

class CanalComunicacao(models.Model):
    """
    Canal de comunicação (1-1 ou Grupo)
    Implementa hierarquia de acesso e visibilidade
    """
    TIPO_CHOICES = [
        ('INDIVIDUAL', 'Individual'),
        ('GRUPO_TURMA', 'Grupo de Turma'),
        ('GRUPO_DISCIPLINA', 'Grupo de Disciplina'),
        ('GRUPO_PROJETO', 'Grupo de Projeto'),
        ('OFICIAL', 'Canal Oficial')  # Direção/Coordenação
    ]

    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('ARQUIVADO', 'Arquivado'),
        ('BLOQUEADO', 'Bloqueado')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('Escola', on_delete=models.CASCADE, related_name='canais')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nome = models.CharField(max_length=200, blank=True)  # Para grupos
    descricao = models.TextField(blank=True)

    # Relacionamentos
    turma = models.ForeignKey('Turma', on_delete=models.SET_NULL, null=True, blank=True, related_name='canais')
    disciplina = models.ForeignKey('Disciplina', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='canais')

    # Criador e administradores
    criado_por = models.ForeignKey('User', on_delete=models.CASCADE, related_name='canais_criados')
    administradores = models.ManyToManyField('User', related_name='canais_administrados', blank=True)

    # Controle de acesso e visibilidade
    visivel_para_gestao = models.BooleanField(default=True)  # Gestor sempre vê
    visivel_para_coordenacao = models.BooleanField(default=True)  # Coordenador pode ver
    permite_anexos = models.BooleanField(default=True)
    permite_entrega_trabalhos = models.BooleanField(default=False)

    # Metadados
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    fixado = models.BooleanField(default=False)
    silenciado_por = models.ManyToManyField('User', related_name='canais_silenciados', blank=True)

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ultima_mensagem_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'canais_comunicacao'
        ordering = ['-fixado', '-ultima_mensagem_em']
        verbose_name = 'Canal de Comunicação'
        verbose_name_plural = 'Canais de Comunicação'

    def __str__(self):
        if self.tipo == 'INDIVIDUAL':
            membros = self.participantes.select_related('usuario')[:2]
            nomes = [m.usuario.get_full_name() for m in membros]
            return f"Chat: {' - '.join(nomes)}"
        return self.nome or f"Canal {self.tipo}"

    def pode_visualizar(self, usuario):
        """Verifica se usuário pode visualizar o canal"""
        # Superuser e Gestor veem tudo
        if usuario.role in ['SUPERUSER', 'GESTOR']:
            return True

        # Coordenador vê canais da sua coordenação
        if usuario.role == 'COORDENADOR' and self.visivel_para_coordenacao:
            if self.turma and self.turma.coordenador == usuario:
                return True

        # Participante direto
        return self.participantes.filter(usuario=usuario).exists()

    def pode_enviar_mensagem(self, usuario):
        """Verifica se usuário pode enviar mensagem"""
        if self.status == 'BLOQUEADO':
            return False

        # Administrador pode sempre enviar
        if self.administradores.filter(id=usuario.id).exists():
            return True

        # Gestor/Coordenador podem intervir
        if usuario.role in ['SUPERUSER', 'GESTOR', 'COORDENADOR']:
            return self.pode_visualizar(usuario)

        # Participante ativo
        participante = self.participantes.filter(usuario=usuario).first()
        return participante and participante.ativo

    def marcar_como_lida(self, usuario):
        """Marca todas as mensagens como lidas para o usuário"""
        self.mensagens.filter(lida=False).exclude(remetente=usuario).update(
            lida=True,
            lida_em=timezone.now()
        )

    def obter_nao_lidas(self, usuario):
        """Retorna quantidade de mensagens não lidas"""
        return self.mensagens.filter(lida=False).exclude(remetente=usuario).count()


class ParticipanteCanal(models.Model):
    """
    Participantes de um canal
    """
    PAPEL_CHOICES = [
        ('MEMBRO', 'Membro'),
        ('MODERADOR', 'Moderador'),
        ('ADMIN', 'Administrador')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canal = models.ForeignKey(CanalComunicacao, on_delete=models.CASCADE, related_name='participantes')
    usuario = models.ForeignKey('User', on_delete=models.CASCADE, related_name='participacoes_canais')

    papel = models.CharField(max_length=20, choices=PAPEL_CHOICES, default='MEMBRO')
    ativo = models.BooleanField(default=True)
    pode_enviar = models.BooleanField(default=True)
    pode_ver_historico = models.BooleanField(default=True)

    # Notificações
    notificar = models.BooleanField(default=True)
    notificar_email = models.BooleanField(default=False)
    notificar_sms = models.BooleanField(default=False)

    # Auditoria
    adicionado_por = models.ForeignKey('User', on_delete=models.SET_NULL, null=True,
                                       related_name='usuarios_adicionados')
    adicionado_em = models.DateTimeField(auto_now_add=True)
    ultima_visualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'participantes_canal'
        unique_together = ['canal', 'usuario']
        ordering = ['papel', 'usuario__first_name']

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.canal}"


class MensagemCanal(models.Model):
    """
    Mensagens dentro dos canais
    """
    TIPO_CHOICES = [
        ('TEXTO', 'Texto'),
        ('ARQUIVO', 'Arquivo'),
        ('TRABALHO', 'Entrega de Trabalho'),
        ('AVISO', 'Aviso'),
        ('SISTEMA', 'Mensagem do Sistema')
    ]

    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('NORMAL', 'Normal'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canal = models.ForeignKey(CanalComunicacao, on_delete=models.CASCADE, related_name='mensagens')
    remetente = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='mensagens_canal_enviadas')

    # Conteúdo
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='TEXTO')
    conteudo = models.TextField()
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='NORMAL')

    # Resposta/Thread
    respondendo_a = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='respostas')

    # Controle
    editada = models.BooleanField(default=False)
    editada_em = models.DateTimeField(null=True, blank=True)
    excluida = models.BooleanField(default=False)
    excluida_em = models.DateTimeField(null=True, blank=True)

    # Leitura
    lida = models.BooleanField(default=False)
    lida_em = models.DateTimeField(null=True, blank=True)
    visualizacoes = models.IntegerField(default=0)

    # Metadados
    ip_remetente = models.GenericIPAddressField(null=True, blank=True)
    enviada_em = models.DateTimeField(auto_now_add=True)

    # Flags especiais
    requer_confirmacao = models.BooleanField(default=False)
    confirmada_por = models.ManyToManyField('User', related_name='mensagens_confirmadas', blank=True)

    class Meta:
        db_table = 'mensagens_canal'
        ordering = ['enviada_em']
        indexes = [
            models.Index(fields=['canal', '-enviada_em']),
            models.Index(fields=['remetente', '-enviada_em']),
        ]

    def __str__(self):
        return f"{self.remetente.get_full_name()}: {self.conteudo[:50]}"

    def marcar_como_lida(self, usuario):
        """Marca mensagem como lida"""
        if not self.lida and self.remetente != usuario:
            self.lida = True
            self.lida_em = timezone.now()
            self.save()

            # Atualiza visualizações
            Visualizacao.objects.get_or_create(
                mensagem=self,
                usuario=usuario,
                defaults={'visualizada_em': timezone.now()}
            )

    def pode_editar(self, usuario):
        """Verifica se usuário pode editar"""
        if self.remetente == usuario:
            # Pode editar até 15 minutos após envio
            return (timezone.now() - self.enviada_em).seconds < 900

        # Admin do canal pode editar
        return self.canal.administradores.filter(id=usuario.id).exists()

    def pode_excluir(self, usuario):
        """Verifica se usuário pode excluir"""
        if self.remetente == usuario:
            return True

        # Admin, Gestor, Coordenador podem excluir
        if usuario.role in ['SUPERUSER', 'GESTOR']:
            return True

        if usuario.role == 'COORDENADOR':
            return self.canal.pode_visualizar(usuario)

        return self.canal.administradores.filter(id=usuario.id).exists()


class AnexoMensagem(models.Model):
    """
    Anexos das mensagens (arquivos, imagens, documentos)
    """
    TIPO_CHOICES = [
        ('IMAGEM', 'Imagem'),
        ('DOCUMENTO', 'Documento'),
        ('VIDEO', 'Vídeo'),
        ('AUDIO', 'Áudio'),
        ('OUTRO', 'Outro')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mensagem = models.ForeignKey(MensagemCanal, on_delete=models.CASCADE, related_name='anexos')

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nome_arquivo = models.CharField(max_length=255)
    url = models.URLField()  # Supabase Storage
    tamanho = models.BigIntegerField()  # bytes
    mime_type = models.CharField(max_length=100)

    # Se for trabalho
    e_trabalho = models.BooleanField(default=False)
    atividade = models.ForeignKey('AtividadeAgenda', on_delete=models.SET_NULL, null=True, blank=True)
    nota_trabalho = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    feedback_professor = models.TextField(blank=True)

    # Metadados
    enviado_em = models.DateTimeField(auto_now_add=True)
    downloads = models.IntegerField(default=0)

    class Meta:
        db_table = 'anexos_mensagem'
        ordering = ['enviado_em']

    def __str__(self):
        return self.nome_arquivo


class Visualizacao(models.Model):
    """
    Registro de visualizações de mensagens
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mensagem = models.ForeignKey(MensagemCanal, on_delete=models.CASCADE, related_name='visualizacoes_detalhadas')
    usuario = models.ForeignKey('User', on_delete=models.CASCADE, related_name='mensagens_visualizadas')
    visualizada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visualizacoes_mensagem'
        unique_together = ['mensagem', 'usuario']
        ordering = ['-visualizada_em']


class ResponsavelConversa(models.Model):
    """
    Rastreamento de quem é responsável por responder uma conversa
    Permite que coordenadores/gestores assumam conversas
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canal = models.ForeignKey(CanalComunicacao, on_delete=models.CASCADE, related_name='responsaveis')

    # Responsável original (professor, coordenador)
    responsavel_original = models.ForeignKey('User', on_delete=models.CASCADE, related_name='conversas_originais')

    # Quem assumiu a conversa (se houver)
    assumida_por = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='conversas_assumidas')
    assumida_em = models.DateTimeField(null=True, blank=True)
    motivo_assuncao = models.TextField(blank=True)

    # Status
    ativo = models.BooleanField(default=True)
    devolvida = models.BooleanField(default=False)
    devolvida_em = models.DateTimeField(null=True, blank=True)

    # SLA (Service Level Agreement)
    prazo_resposta = models.IntegerField(default=24, help_text="Horas para responder")
    alertado = models.BooleanField(default=False)
    atrasado = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'responsavel_conversa'
        ordering = ['-criado_em']

    def __str__(self):
        if self.assumida_por:
            return f"{self.canal} - Assumida por {self.assumida_por.get_full_name()}"
        return f"{self.canal} - {self.responsavel_original.get_full_name()}"

    def assumir(self, usuario, motivo=""):
        """Permite que coordenador/gestor assuma a conversa"""
        self.assumida_por = usuario
        self.assumida_em = timezone.now()
        self.motivo_assuncao = motivo
        self.save()

    def devolver(self):
        """Devolve conversa ao responsável original"""
        self.devolvida = True
        self.devolvida_em = timezone.now()
        self.assumida_por = None
        self.save()

    def esta_atrasado(self):
        """Verifica se resposta está atrasada"""
        if not self.canal.ultima_mensagem_em:
            return False

        tempo_decorrido = timezone.now() - self.canal.ultima_mensagem_em
        return tempo_decorrido.total_seconds() / 3600 > self.prazo_resposta


class NotificacaoComunicacao(models.Model):
    """
    Notificações de comunicação
    """
    TIPO_CHOICES = [
        ('NOVA_MENSAGEM', 'Nova Mensagem'),
        ('MENCAO', 'Menção'),
        ('RESPOSTA', 'Resposta'),
        ('TRABALHO_ENTREGUE', 'Trabalho Entregue'),
        ('CONVERSA_ASSUMIDA', 'Conversa Assumida'),
        ('SLA_ALERTA', 'Alerta de SLA'),
        ('CANAL_CRIADO', 'Canal Criado')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey('User', on_delete=models.CASCADE, related_name='notificacoes_comunicacao')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)

    canal = models.ForeignKey(CanalComunicacao, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.ForeignKey(MensagemCanal, on_delete=models.CASCADE, null=True, blank=True)

    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()

    lida = models.BooleanField(default=False)
    lida_em = models.DateTimeField(null=True, blank=True)

    enviada_por_email = models.BooleanField(default=False)
    enviada_por_sms = models.BooleanField(default=False)

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificacoes_comunicacao'
        ordering = ['-criada_em']
        indexes = [
            models.Index(fields=['usuario', 'lida', '-criada_em']),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_tipo_display()}"

    def marcar_como_lida(self):
        """Marca notificação como lida"""
        if not self.lida:
            self.lida = True
            self.lida_em = timezone.now()
            self.save()


class AuditoriaConversa(models.Model):
    """
    Auditoria completa de todas as ações em conversas
    """
    ACAO_CHOICES = [
        ('MENSAGEM_ENVIADA', 'Mensagem Enviada'),
        ('MENSAGEM_EDITADA', 'Mensagem Editada'),
        ('MENSAGEM_EXCLUIDA', 'Mensagem Excluída'),
        ('CANAL_CRIADO', 'Canal Criado'),
        ('PARTICIPANTE_ADICIONADO', 'Participante Adicionado'),
        ('PARTICIPANTE_REMOVIDO', 'Participante Removido'),
        ('CONVERSA_ASSUMIDA', 'Conversa Assumida'),
        ('CONVERSA_DEVOLVIDA', 'Conversa Devolvida'),
        ('ARQUIVO_ENVIADO', 'Arquivo Enviado'),
        ('TRABALHO_ENTREGUE', 'Trabalho Entregue')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=30, choices=ACAO_CHOICES)

    canal = models.ForeignKey(CanalComunicacao, on_delete=models.CASCADE, related_name='auditorias')
    mensagem = models.ForeignKey(MensagemCanal, on_delete=models.SET_NULL, null=True, blank=True)

    detalhes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditoria_conversa'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['canal', '-criado_em']),
            models.Index(fields=['usuario', '-criado_em']),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name() if self.usuario else 'Sistema'} - {self.get_acao_display()}"