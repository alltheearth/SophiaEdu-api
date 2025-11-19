from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Escola
from .serializers import EscolaSerializer
from ..permissions import IsSuperUser

class EscolaViewSet(viewsets.ModelViewSet):
    """CRUD de Escolas"""
    queryset = Escola.objects.all()
    serializer_class = EscolaSerializer
    permission_classes = [IsSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo', 'plano']
    search_fields = ['nome', 'cnpj']