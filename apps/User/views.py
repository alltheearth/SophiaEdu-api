from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .models import User
from .serializers import UserSerializer
from ..permissions import IsGestorOrAbove

class UsuarioViewSet(viewsets.ModelViewSet):
    """CRUD de Usuários"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsGestorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'ativo', 'email_verificado']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'cpf']
    ordering_fields = ['created_at', 'first_name']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERUSER':
            return self.queryset

        escola_ids = user.escolas.values_list('escola_id', flat=True)
        return self.queryset.filter(escolas__escola_id__in=escola_ids).distinct()

    def retrieve(self, request, *args, **kwargs):
        """Retorna usuário com suas escolas vinculadas"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Adiciona escolas do usuário
        vinculos = instance.escolas.filter(ativo=True).select_related('escola')
        data['escolas'] = [
            {
                'id': str(v.escola.id),
                'nome': v.escola.nome,
                'logo': v.escola.logo,
                'cnpj': v.escola.cnpj,
                'role': v.role_na_escola
            }
            for v in vinculos
        ]

        return Response(data)

    @action(detail=True, methods=['post'])
    def resetar_senha(self, request, pk=None):
        """Reseta senha do usuário"""
        usuario = self.get_object()
        nova_senha = usuario.gerar_senha_temporaria()
        usuario.set_password(nova_senha)
        usuario.senha_temporaria = True
        usuario.save()

        return Response({
            'success': True,
            'message': 'Senha resetada',
            'senha_temporaria': nova_senha
        })

