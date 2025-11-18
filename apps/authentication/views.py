from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.authtoken.models import Token

from ..User.models import (User)
from ..User.serializers import (UserSerializer, UserCreateSerializer, )

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

