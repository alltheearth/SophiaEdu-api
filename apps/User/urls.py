# apps/User/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import UsuarioViewSet

router = DefaultRouter()
router.register(r'User', UsuarioViewSet, basename='User')

urlpatterns = [

] + router.urls