from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.authtoken.models import Token
from decimal import Decimal
from django.db.models import Count, Avg, Q, Sum
# Imports das permissões
from ..permissions import (
    IsSuperUser, IsGestorOrAbove, IsCoordenadorOrAbove,
    IsProfessorOrAbove, CanEditNota, CanAccessAlunoData
)
# Imports dos modelos
from .models import (
    User,  TokenRedefinicaoSenha,
    HistoricoLogin, SessaoUsuario
)

# Imports dos serializers
from .serializers import (
    UserSerializer, UserCreateSerializer,
)

# ============================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def registro(request):
    """Registra novo usuário"""
    serializer = UserCreateSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'message': 'Usuário criado com sucesso',
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Realiza login do usuário"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'success': False,
            'message': 'Username e password são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Credenciais inválidas'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if user.esta_bloqueado():
        tempo_restante = (user.bloqueado_ate - timezone.now()).seconds // 60
        return Response({
            'success': False,
            'message': f'Usuário bloqueado. Tente novamente em {tempo_restante} minutos.'
        }, status=status.HTTP_403_FORBIDDEN)

    if not user.ativo:
        return Response({
            'success': False,
            'message': 'Usuário inativo'
        }, status=status.HTTP_403_FORBIDDEN)

    user_auth = authenticate(username=username, password=password)

    if user_auth:
        user.resetar_tentativas()
        user.last_login = timezone.now()
        user.save()

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'user': UserSerializer(user).data,
            'token': token.key,
            'primeiro_acesso': user.primeiro_acesso
        })
    else:
        user.registrar_tentativa_falha()
        return Response({
            'success': False,
            'message': 'Credenciais inválidas',
            'tentativas_restantes': 5 - user.tentativas_login_falhas
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Realiza logout"""
    try:
        request.user.auth_token.delete()
        return Response({'success': True, 'message': 'Logout realizado'})
    except:
        return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def perfil_usuario(request):
    """Retorna perfil do usuário"""
    user = request.user
    data = UserSerializer(user).data

    if user.role == 'ALUNO' and hasattr(user, 'aluno_profile'):
        data['aluno'] = {
            'matricula': user.aluno_profile.matricula,
            'turma': user.aluno_profile.turma_atual.nome if user.aluno_profile.turma_atual else None
        }
    elif user.role == 'PROFESSOR' and hasattr(user, 'professor_profile'):
        data['professor'] = {
            'formacao': user.professor_profile.formacao,
            'status': user.professor_profile.status
        }
    elif user.role == 'RESPONSAVEL' and hasattr(user, 'responsavel_profile'):
        alunos = user.responsavel_profile.alunos.all()
        data['responsavel'] = {
            'alunos': [{'id': str(a.id), 'nome': a.usuario.get_full_name()} for a in alunos]
        }

    return Response({'success': True, 'data': data})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def atualizar_perfil(request):
    """Atualiza perfil do usuário"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({'success': True, 'data': serializer.data})

    return Response({'success': False, 'errors': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST)


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

