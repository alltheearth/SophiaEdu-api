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
    # Funções de Autenticação
    registro,
    login,
    logout,
    perfil_usuario,
    atualizar_perfil,
    # ViewSets
    EscolaViewSet,
    ContatoViewSet,
    CalendarioEventoViewSet,
    FAQViewSet,
    DocumentoViewSet,
    DashboardViewSet,
    UsuarioViewSet,
    LeadViewSet,
)

# ============================================
# ROUTER PARA VIEWSETS
# ============================================
router = DefaultRouter()
router.register(r'escolas', EscolaViewSet, basename='escola')
router.register(r'contatos', ContatoViewSet, basename='contato')
router.register(r'eventos', CalendarioEventoViewSet, basename='evento')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'documentos', DocumentoViewSet, basename='documento')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'leads', LeadViewSet, basename='lead')
# ============================================
# URL PATTERNS
# ============================================
urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # ============ AUTENTICAÇÃO ============
    path('api/auth/registro/', registro, name='registro'),
    path('api/auth/login/', login, name='login'),
    path('api/auth/logout/', logout, name='logout'),
    path('api/auth/perfil/', perfil_usuario, name='perfil'),
    path('api/auth/atualizar-perfil/', atualizar_perfil, name='atualizar-perfil'),

    # ============ API PRINCIPAL ============
    path('api/', include(router.urls)),

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