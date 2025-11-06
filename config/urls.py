from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as authtoken_views

from sophia.views import (
    # Autenticação
    registro,
    login_view,
    logout_view,
    perfil_usuario,
    atualizar_perfil,

    # ViewSets - Gestão
    EscolaViewSet,
    UsuarioViewSet,

    # ViewSets - Acadêmico
    AnoLetivoViewSet,
    TurmaViewSet,
    DisciplinaViewSet,
    ProfessorViewSet,
    AlunoViewSet,
    ResponsavelViewSet,

    # ViewSets - Notas e Frequência
    NotaViewSet,
    FrequenciaViewSet,

    # ViewSets - Financeiro
    MensalidadeViewSet,

    # ViewSets - Comunicação
    AvisoViewSet,
    MensagemViewSet,

    # ViewSets - Agenda e Eventos
    AtividadeAgendaViewSet,
    EventoViewSet,

    # ViewSets - Dashboard e Outros
    DashboardViewSet,
    LeadViewSet,
    ContatoViewSet,
    FAQViewSet,
    DocumentoViewSet,
)

from sophia.webhooks.asaas_webhook import asaas_webhook

# ============================================
# ROUTER
# ============================================
router = DefaultRouter()

# Gestão
router.register(r'escolas', EscolaViewSet, basename='escola')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')

# Acadêmico
router.register(r'anos-letivos', AnoLetivoViewSet, basename='ano-letivo')
router.register(r'turmas', TurmaViewSet, basename='turma')
router.register(r'disciplinas', DisciplinaViewSet, basename='disciplina')
router.register(r'professores', ProfessorViewSet, basename='professor')
router.register(r'alunos', AlunoViewSet, basename='aluno')
router.register(r'responsaveis', ResponsavelViewSet, basename='responsavel')

# Notas e Frequência
router.register(r'notas', NotaViewSet, basename='nota')
router.register(r'frequencias', FrequenciaViewSet, basename='frequencia')

# Financeiro
router.register(r'mensalidades', MensalidadeViewSet, basename='mensalidade')

# Comunicação
router.register(r'avisos', AvisoViewSet, basename='aviso')
router.register(r'mensagens', MensagemViewSet, basename='mensagem')

# Agenda e Eventos
router.register(r'atividades', AtividadeAgendaViewSet, basename='atividade')
router.register(r'eventos', EventoViewSet, basename='evento')

# Dashboard e Outros
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'contatos', ContatoViewSet, basename='contato')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'documentos', DocumentoViewSet, basename='documento')

# ============================================
# URL PATTERNS
# ============================================
urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # ============ AUTENTICAÇÃO ============
    path('api/auth/registro/', registro, name='registro'),
    path('api/auth/login/', login_view, name='login'),
    path('api/auth/logout/', logout_view, name='logout'),
    path('api/auth/perfil/', perfil_usuario, name='perfil'),
    path('api/auth/atualizar-perfil/', atualizar_perfil, name='atualizar-perfil'),

    # ============ API PRINCIPAL ============
    path('api/', include(router.urls)),

    # ============ WEBHOOKS ============
    path('webhooks/asaas/', asaas_webhook, name='asaas-webhook'),

    # ============ DRF PADRÃO ============
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', authtoken_views.obtain_auth_token, name='api-token-auth'),
]

# ============================================
# ARQUIVOS ESTÁTICOS (DESENVOLVIMENTO)
# ============================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

