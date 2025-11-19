from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EscolaViewSet

router = DefaultRouter()

router.register(r'', EscolaViewSet, basename='Escola')
urlpatterns = [

] + router.urls