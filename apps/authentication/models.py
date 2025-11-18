from django.db import models
from django.utils import timezone
import uuid
import secrets

from django.contrib.auth.models import User

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
