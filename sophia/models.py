# models.py (simplificado)

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


# ============= CORE =============

class User(AbstractUser):
    """Usuário base do sistema"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=[
        ('SUPERUSER', 'Super Usuário'),
        ('GESTOR', 'Gestor'),
        ('COORDENADOR', 'Coordenador'),
        ('PROFESSOR', 'Professor'),
        ('RESPONSAVEL', 'Responsável'),
        ('ALUNO', 'Aluno'),
    ])
    foto = models.URLField(blank=True, null=True)  # Supabase Storage URL
    telefone = models.CharField(max_length=15, blank=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'


class Escola(models.Model):
    """Escola - Tenant principal"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, unique=True)
    endereco = models.TextField()
    telefone = models.CharField(max_length=15)
    email = models.EmailField()
    logo = models.URLField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    plano = models.CharField(max_length=20, default='BASIC')  # BASIC, PRO, ENTERPRISE
    created_at = models.DateTimeField(auto_now_add=True)

    # Configurações Asaas
    asaas_api_key = models.CharField(max_length=200, blank=True)
    asaas_wallet_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'escolas'
        verbose_name_plural = 'Escolas'


class EscolaUsuario(models.Model):
    """Relacionamento Many-to-Many entre Escola e Usuário"""
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='usuarios')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escolas')
    role_na_escola = models.CharField(max_length=20)  # Pode ter roles diferentes em escolas diferentes

    class Meta:
        db_table = 'escola_usuarios'
        unique_together = ['escola', 'usuario']


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