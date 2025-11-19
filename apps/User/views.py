from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer
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

    def get_serializer_class(self):
        """Retorna serializer apropriado para cada ação"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        """Filtra usuários baseado no role do usuário autenticado"""
        user = self.request.user

        if user.role == 'SUPERUSER':
            return self.queryset

        # Outros usuários só veem usuários das mesmas escolas
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
                'role': v.role_na_escola,
                'data_vinculo': v.data_vinculo
            }
            for v in vinculos
        ]

        return Response(data)

    def perform_create(self, serializer):
        """Customiza criação para incluir validações extras"""
        user = self.request.user
        novo_usuario = serializer.save()

        # Verifica se tem permissão para criar este tipo de usuário
        if not user.pode_criar_usuario(novo_usuario.role):
            novo_usuario.delete()
            raise PermissionError(
                f"Você não tem permissão para criar usuários com role {novo_usuario.get_role_display()}"
            )

    @action(detail=True, methods=['post'])
    def resetar_senha(self, request, pk=None):
        """Reseta senha do usuário"""
        usuario = self.get_object()
        nova_senha = usuario.gerar_senha_temporaria()
        usuario.set_password(nova_senha)
        usuario.senha_temporaria = True
        usuario.primeiro_acesso = True
        usuario.save()

        return Response({
            'success': True,
            'message': 'Senha resetada com sucesso',
            'senha_temporaria': nova_senha
        })

    @action(detail=True, methods=['post'])
    def vincular_escola(self, request, pk=None):
        """Vincula usuário a uma escola"""
        from ..Schools.models import Escola, EscolaUsuario

        usuario = self.get_object()
        escola_id = request.data.get('escola_id')
        role_na_escola = request.data.get('role_na_escola', usuario.role)

        if not escola_id:
            return Response(
                {'error': 'escola_id é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            escola = Escola.objects.get(id=escola_id, ativo=True)
        except Escola.DoesNotExist:
            return Response(
                {'error': 'Escola não encontrada ou inativa'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifica se já existe vínculo
        vinculo_existente = EscolaUsuario.objects.filter(
            escola=escola,
            usuario=usuario
        ).first()

        if vinculo_existente:
            if not vinculo_existente.ativo:
                vinculo_existente.ativo = True
                vinculo_existente.save()
                return Response({
                    'success': True,
                    'message': 'Vínculo reativado com sucesso'
                })
            return Response(
                {'error': 'Usuário já vinculado a esta escola'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cria novo vínculo
        EscolaUsuario.objects.create(
            escola=escola,
            usuario=usuario,
            role_na_escola=role_na_escola
        )

        return Response({
            'success': True,
            'message': 'Usuário vinculado à escola com sucesso'
        })

    @action(detail=True, methods=['post'])
    def desvincular_escola(self, request, pk=None):
        """Desvincula usuário de uma escola"""
        from ..Schools.models import EscolaUsuario

        usuario = self.get_object()
        escola_id = request.data.get('escola_id')

        # Verifica se não é SUPERUSER (não precisa de escola)
        if usuario.role == 'SUPERUSER':
            return Response(
                {'error': 'SUPERUSER não precisa de vínculo com escola'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Conta quantas escolas ativas o usuário tem
        vinculos_ativos = usuario.escolas.filter(ativo=True).count()

        if vinculos_ativos <= 1:
            return Response(
                {'error': 'Usuário precisa estar vinculado a pelo menos uma escola'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not escola_id:
            return Response(
                {'error': 'escola_id é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            vinculo = EscolaUsuario.objects.get(
                escola_id=escola_id,
                usuario=usuario,
                ativo=True
            )
            vinculo.ativo = False
            vinculo.save()

            return Response({
                'success': True,
                'message': 'Usuário desvinculado da escola com sucesso'
            })
        except EscolaUsuario.DoesNotExist:
            return Response(
                {'error': 'Vínculo não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def verificar_escolas(self, request, pk=None):
        """Verifica status das escolas vinculadas ao usuário"""
        usuario = self.get_object()

        vinculos = usuario.escolas.all().select_related('escola')

        data = {
            'usuario_id': str(usuario.id),
            'username': usuario.username,
            'role': usuario.role,
            'requer_escola': usuario.role != 'SUPERUSER',
            'tem_escola_vinculada': usuario.tem_escola_vinculada(),
            'total_vinculos': vinculos.count(),
            'vinculos_ativos': vinculos.filter(ativo=True).count(),
            'escolas': [
                {
                    'escola_id': str(v.escola.id),
                    'escola_nome': v.escola.nome,
                    'role_na_escola': v.role_na_escola,
                    'ativo': v.ativo,
                    'data_vinculo': v.data_vinculo
                }
                for v in vinculos
            ]
        }

        return Response(data)