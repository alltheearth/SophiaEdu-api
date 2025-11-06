from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Escola, EscolaUsuario, Professor, Aluno, Responsavel,
    AlunoResponsavel, AnoLetivo, Turma, Disciplina, TurmaDisciplina,
    PeriodoAvaliativo, Nota, Frequencia, Mensalidade, Aviso,
    Mensagem, AtividadeAgenda, Evento, TokenRedefinicaoSenha,
    HistoricoLogin, SessaoUsuario
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


@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'plano', 'ativo', 'created_at']
    list_filter = ['ativo', 'plano']
    search_fields = ['nome', 'cnpj', 'email']
    readonly_fields = ['created_at']


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ['get_nome', 'escola', 'formacao', 'carga_horaria', 'status']
    list_filter = ['status', 'turno', 'escola']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'registro_profissional']

    def get_nome(self, obj):
        return obj.usuario.get_full_name()

    get_nome.short_description = 'Nome'


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ['get_nome', 'matricula', 'escola', 'turma_atual', 'status']
    list_filter = ['status', 'escola', 'turma_atual']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'matricula', 'cpf']

    def get_nome(self, obj):
        return obj.usuario.get_full_name()

    get_nome.short_description = 'Nome'


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'serie', 'turno', 'escola', 'ano_letivo', 'capacidade_maxima']
    list_filter = ['turno', 'escola', 'ano_letivo']
    search_fields = ['nome', 'serie']


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'escola', 'carga_horaria']
    list_filter = ['escola']
    search_fields = ['nome', 'codigo']


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ['get_aluno', 'get_disciplina', 'nota', 'tipo_avaliacao', 'data_avaliacao']
    list_filter = ['tipo_avaliacao', 'periodo', 'turma_disciplina__disciplina']
    search_fields = ['aluno__usuario__first_name', 'aluno__usuario__last_name']
    date_hierarchy = 'data_avaliacao'

    def get_aluno(self, obj):
        return obj.aluno.usuario.get_full_name()

    get_aluno.short_description = 'Aluno'

    def get_disciplina(self, obj):
        return obj.turma_disciplina.disciplina.nome

    get_disciplina.short_description = 'Disciplina'


@admin.register(Frequencia)
class FrequenciaAdmin(admin.ModelAdmin):
    list_display = ['get_aluno', 'get_disciplina', 'data', 'presente']
    list_filter = ['presente', 'data']
    search_fields = ['aluno__usuario__first_name', 'aluno__usuario__last_name']
    date_hierarchy = 'data'

    def get_aluno(self, obj):
        return obj.aluno.usuario.get_full_name()

    get_aluno.short_description = 'Aluno'

    def get_disciplina(self, obj):
        return obj.turma_disciplina.disciplina.nome

    get_disciplina.short_description = 'Disciplina'


@admin.register(Mensalidade)
class MensalidadeAdmin(admin.ModelAdmin):
    list_display = ['get_aluno', 'competencia', 'valor_final', 'data_vencimento', 'status', 'dias_atraso']
    list_filter = ['status', 'competencia']
    search_fields = ['aluno__usuario__first_name', 'aluno__usuario__last_name']
    date_hierarchy = 'data_vencimento'
    readonly_fields = ['asaas_payment_id', 'boleto_url', 'pix_qrcode']

    def get_aluno(self, obj):
        return obj.aluno.usuario.get_full_name()

    get_aluno.short_description = 'Aluno'


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'data', 'hora_inicio', 'status', 'escola']
    list_filter = ['tipo', 'status', 'escola']
    search_fields = ['titulo', 'descricao']
    date_hierarchy = 'data'


@admin.register(HistoricoLogin)
class HistoricoLoginAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'sucesso', 'ip_address', 'cidade', 'timestamp']
    list_filter = ['sucesso', 'timestamp']
    search_fields = ['usuario__email', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = ['usuario', 'sucesso', 'ip_address', 'user_agent', 'timestamp']


# Registros simples
admin.site.register(Responsavel)
admin.site.register(AlunoResponsavel)
admin.site.register(AnoLetivo)
admin.site.register(TurmaDisciplina)
admin.site.register(PeriodoAvaliativo)
admin.site.register(Aviso)
admin.site.register(Mensagem)
admin.site.register(AtividadeAgenda)
admin.site.register(EscolaUsuario)
admin.site.register(TokenRedefinicaoSenha)
admin.site.register(SessaoUsuario)