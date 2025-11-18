# apps/User/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    registro, login_view, logout_view,
    perfil_usuario, atualizar_perfil,
    UsuarioViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')

urlpatterns = [
    # Autenticação
    path('auth/registro/', registro, name='registro'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/perfil/', perfil_usuario, name='perfil'),
    path('auth/atualizar-perfil/', atualizar_perfil, name='atualizar-perfil'),
] + router.urls