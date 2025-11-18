# apps/User/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    registro, login_view, logout_view,
    perfil_usuario, atualizar_perfil,
)

router = DefaultRouter()


urlpatterns = [
    # Autenticação
    path('/registro/', registro, name='registro'),
    path('/login/', login_view, name='login'),
    path('/logout/', logout_view, name='logout'),
    path('/perfil/', perfil_usuario, name='perfil'),
    path('/atualizar-perfil/', atualizar_perfil, name='atualizar-perfil'),
] + router.urls