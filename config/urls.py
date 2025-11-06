from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as authtoken_views

# ============================================
# IMPORTAÇÕES DE VIEWS
# ============================================
from sophia.views import (
    # ViewSets que EXISTEM no views.py
    NotaViewSet,
    AlunoViewSet,
    MensalidadeViewSet,

    # Funções de Autenticação
    #registro,
    #login_view,
    #logout_view,
    #perfil_usuario,
    #atualizar_perfil,
)

# Webhook
from sophia.webhooks.asaas_webhook import asaas_webhook

# ============================================
# ROUTER PARA VIEWSETS
# ============================================
router = DefaultRouter()

# ViewSets implementados
router.register(r'notas', NotaViewSet, basename='nota')
router.register(r'alunos', AlunoViewSet, basename='aluno')
router.register(r'mensalidades', MensalidadeViewSet, basename='mensalidade')

# ============================================
# URL PATTERNS
# ============================================
urlpatterns = [
    # ============ DJANGO ADMIN ============
    path('admin/', admin.site.urls),

    # ============ AUTENTICAÇÃO ============
    #path('api/auth/registro/', registro, name='registro'),
    #path('api/auth/login/', login_view, name='login'),
    #path('api/auth/logout/', logout_view, name='logout'),
    #path('api/auth/perfil/', perfil_usuario, name='perfil'),
    #path('api/auth/atualizar-perfil/', atualizar_perfil, name='atualizar-perfil'),

    # ============ API PRINCIPAL ============
    path('api/', include(router.urls)),

    # ============ WEBHOOKS ============
    path('webhooks/asaas/', asaas_webhook, name='asaas-webhook'),

    # ============ DRF PADRÃO ============
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', authtoken_views.obtain_auth_token, name='api-token-auth'),
]

# ============================================
# SERVIR ARQUIVOS ESTÁTICOS E MEDIA (DESENVOLVIMENTO)
# ============================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ============================================
# NOTA DE IMPLEMENTAÇÃO:
# ============================================
# ViewSets que PRECISAM SER CRIADOS posteriormente:
# - EscolaViewSet
# - ContatoViewSet
# - CalendarioEventoViewSet
# - FAQViewSet
# - DocumentoViewSet
# - DashboardViewSet
# - UsuarioViewSet
# - LeadViewSet
# - TurmaViewSet
# - ProfessorViewSet
# - ResponsavelViewSet
# - DisciplinaViewSet
# - FrequenciaViewSet
# - AvisoViewSet
# - MensagemViewSet
# - AtividadeAgendaViewSet
# - EventoViewSet
#
# Para adicionar cada um, descomente e registre:
# router.register(r'escolas', EscolaViewSet, basename='escola')
# ============================================