from django.db import models
import uuid
from ..User.models import User

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