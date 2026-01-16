# apps/authentication/urls.py
from django.urls import path
from .views import (
    registro, login_view, logout_view,
    perfil_usuario, atualizar_perfil,
)

urlpatterns = [
    # Autenticação - SEM A BARRA INICIAL
    path('registro/', registro, name='registro'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('perfil/', perfil_usuario, name='perfil'),
    path('atualizar-perfil/', atualizar_perfil, name='atualizar-perfil'),
]