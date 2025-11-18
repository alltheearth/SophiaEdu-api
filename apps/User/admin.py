from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin customizado para User"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'ativo', 'created_at']
    list_filter = ['role', 'ativo', 'email_verificado']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'cpf']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('role', 'cpf', 'telefone', 'foto')
        }),
        ('Controle de Acesso', {
            'fields': ('ativo', 'email_verificado', 'primeiro_acesso', 'senha_temporaria')
        }),
        ('Segurança', {
            'fields': ('tentativas_login_falhas', 'bloqueado_ate', 'ultimo_login_ip')
        }),
    )









