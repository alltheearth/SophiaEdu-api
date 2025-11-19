from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid
import secrets
import string

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
        related_name='sophia_users',
        related_query_name='sophia_user',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='sophia_users',
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


