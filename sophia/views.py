from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.authtoken.models import Token
from decimal import Decimal

# Imports dos modelos
from .models import (
    User,
    Nota,
    Aluno,
    Turma,
    Mensalidade,
    Escola,
    Professor,
    Responsavel,
)

# Imports dos serializers
from .serializers import (
    NotaSerializer,
    AlunoSerializer,
    AlunoListSerializer,
    MensalidadeSerializer,
    UserSerializer,
    UserCreateSerializer,
)

# Imports das permissões
from .permissions import (
    IsProfessorOrAbove,
    CanEditNota,
    CanAccessAlunoData,
    IsGestorOrAbove,
)

# Imports dos serviços
from .services.asaas_service import AsaasService


# ============================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def registro(request):
    """
    Registra novo usuário no sistema

    Payload:
    {
        "username": "joao.silva",
        "email": "joao@email.com",
        "password": "senha123",
        "first_name": "João",
        "last_name": "Silva",
        "role": "ALUNO",
        "cpf": "123.456.789-00"
    }
    """
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
    """
    Realiza login do usuário

    Payload:
    {
        "username": "joao.silva",
        "password": "senha123"
    }
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'success': False,
            'message': 'Username e password são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Busca usuário
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Credenciais inválidas'
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Verifica se está bloqueado
    if user.esta_bloqueado():
        tempo_restante = (user.bloqueado_ate - timezone.now()).seconds // 60
        return Response({
            'success': False,
            'message': f'Usuário bloqueado. Tente novamente em {tempo_restante} minutos.'
        }, status=status.HTTP_403_FORBIDDEN)

    # Verifica se está ativo
    if not user.ativo:
        return Response({
            'success': False,
            'message': 'Usuário inativo. Entre em contato com o administrador.'
        }, status=status.HTTP_403_FORBIDDEN)

    # Autentica
    user_auth = authenticate(username=username, password=password)

    if user_auth:
        # Reset tentativas falhas
        user.resetar_tentativas()

        # Atualiza último login
        user.last_login = timezone.now()
        user.save()

        # Gera/recupera token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'message': 'Login realizado com sucesso',
            'user': UserSerializer(user).data,
            'token': token.key,
            'primeiro_acesso': user.primeiro_acesso
        }, status=status.HTTP_200_OK)
    else:
        # Registra tentativa falha
        user.registrar_tentativa_falha()

        return Response({
            'success': False,
            'message': 'Credenciais inválidas',
            'tentativas_restantes': 5 - user.tentativas_login_falhas
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Realiza logout removendo o token
    """
    try:
        request.user.auth_token.delete()
        return Response({
            'success': True,
            'message': 'Logout realizado com sucesso'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def perfil_usuario(request):
    """
    Retorna dados do perfil do usuário logado
    """
    user = request.user
    serializer = UserSerializer(user)

    # Adiciona informações extras baseado no role
    data = serializer.data

    if user.role == 'ALUNO' and hasattr(user, 'aluno_profile'):
        data['aluno'] = {
            'matricula': user.aluno_profile.matricula,
            'turma': user.aluno_profile.turma_atual.nome if user.aluno_profile.turma_atual else None,
            'status': user.aluno_profile.status
        }

    elif user.role == 'PROFESSOR' and hasattr(user, 'professor_profile'):
        data['professor'] = {
            'formacao': user.professor_profile.formacao,
            'carga_horaria': user.professor_profile.carga_horaria,
            'status': user.professor_profile.status
        }

    elif user.role == 'RESPONSAVEL' and hasattr(user, 'responsavel_profile'):
        alunos = user.responsavel_profile.alunos.all()
        data['responsavel'] = {
            'alunos': [
                {
                    'id': str(aluno.id),
                    'nome': aluno.usuario.get_full_name(),
                    'matricula': aluno.matricula
                } for aluno in alunos
            ]
        }

    return Response({
        'success': True,
        'data': data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def atualizar_perfil(request):
    """
    Atualiza dados do perfil do usuário

    Payload:
    {
        "first_name": "João",
        "last_name": "Silva",
        "telefone": "(11) 98765-4321",
        "foto": "https://url-da-foto.com/foto.jpg"
    }
    """
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Perfil atualizado com sucesso',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# VIEWSETS
# ============================================

class NotaViewSet(viewsets.ModelViewSet):
    """CRUD de Notas com permissões"""
    queryset = Nota.objects.select_related(
        'aluno', 'turma_disciplina', 'periodo'
    ).all()
    serializer_class = NotaSerializer
    permission_classes = [IsProfessorOrAbove, CanEditNota]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['aluno', 'turma_disciplina', 'periodo']
    ordering_fields = ['data_avaliacao', 'nota']

    def get_queryset(self):
        """Filtra notas baseado no role do usuário"""
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'SUPERUSER':
            return queryset

        if user.role == 'GESTOR':
            escolas = user.escolas.all()
            return queryset.filter(aluno__escola__in=escolas)

        if user.role == 'COORDENADOR':
            return queryset.filter(aluno__turma_atual__coordenador=user)

        if user.role == 'PROFESSOR':
            return queryset.filter(turma_disciplina__professor=user)

        if user.role == 'RESPONSAVEL':
            responsavel = user.responsavel_profile
            alunos = responsavel.alunos.all()
            return queryset.filter(aluno__in=alunos)

        return queryset.none()

    @action(detail=False, methods=['get'])
    def boletim(self, request):
        """Endpoint para gerar boletim do aluno"""
        aluno_id = request.query_params.get('aluno_id')
        periodo_id = request.query_params.get('periodo_id')

        if not aluno_id or not periodo_id:
            return Response({
                'success': False,
                'message': 'aluno_id e periodo_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            aluno = Aluno.objects.get(id=aluno_id)
            self.check_object_permissions(request, aluno)
        except Aluno.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Aluno não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

        notas = self.queryset.filter(
            aluno_id=aluno_id,
            periodo_id=periodo_id
        )

        # Agrupa por disciplina e calcula média
        boletim = {}
        for nota in notas:
            disciplina = nota.turma_disciplina.disciplina.nome
            if disciplina not in boletim:
                boletim[disciplina] = []
            boletim[disciplina].append(float(nota.nota))

        # Calcula médias
        resultado = {
            disciplina: {
                'notas': notas_list,
                'media': sum(notas_list) / len(notas_list),
                'quantidade_avaliacoes': len(notas_list)
            }
            for disciplina, notas_list in boletim.items()
        }

        return Response({
            'success': True,
            'aluno': aluno.usuario.get_full_name(),
            'boletim': resultado
        })


class AlunoViewSet(viewsets.ModelViewSet):
    """CRUD de Alunos"""
    queryset = Aluno.objects.select_related(
        'usuario', 'escola', 'turma_atual'
    ).prefetch_related('responsaveis').all()
    serializer_class = AlunoSerializer
    permission_classes = [IsProfessorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['escola', 'turma_atual', 'status']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'matricula']
    ordering_fields = ['usuario__first_name', 'matricula']

    def get_queryset(self):
        """Filtra alunos baseado no role"""
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'SUPERUSER':
            return queryset

        if user.role in ['GESTOR', 'COORDENADOR']:
            escolas = user.escolas.all()
            return queryset.filter(escola__in=escolas)

        if user.role == 'PROFESSOR':
            turmas = user.disciplinas_lecionadas.values_list('turma', flat=True)
            return queryset.filter(turma_atual__in=turmas)

        if user.role == 'RESPONSAVEL':
            responsavel = user.responsavel_profile
            return responsavel.alunos.all()

        return queryset.none()

    def get_serializer_class(self):
        """Usa serializer diferente para listagem"""
        if self.action == 'list':
            return AlunoListSerializer
        return AlunoSerializer


class MensalidadeViewSet(viewsets.ModelViewSet):
    """CRUD de Mensalidades"""
    queryset = Mensalidade.objects.select_related(
        'aluno', 'responsavel_financeiro', 'aluno__escola'
    ).all()
    serializer_class = MensalidadeSerializer
    permission_classes = [IsGestorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['aluno', 'responsavel_financeiro', 'status', 'competencia']
    ordering_fields = ['data_vencimento', 'valor_final']

    def get_queryset(self):
        """Filtra mensalidades baseado no role"""
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'SUPERUSER':
            return queryset

        if user.role == 'GESTOR':
            escolas = user.escolas.all()
            return queryset.filter(aluno__escola__in=escolas)

        if user.role == 'RESPONSAVEL':
            responsavel = user.responsavel_profile
            return queryset.filter(responsavel_financeiro=responsavel)

        return queryset.none()

    @action(detail=True, methods=['post'])
    def gerar_boleto(self, request, pk=None):
        """Gera boleto para mensalidade"""
        mensalidade = self.get_object()
        escola = mensalidade.aluno.escola

        if not escola.asaas_api_key:
            return Response({
                'success': False,
                'message': 'Escola não possui integração com Asaas configurada'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            asaas = AsaasService(escola.asaas_api_key)
            payment = asaas.gerar_cobranca(mensalidade)

            return Response({
                'success': True,
                'boleto_url': payment.get('bankSlipUrl'),
                'pix_qrcode': payment.get('pixTransaction', {}).get('qrCode', {}).get('payload'),
                'payment_id': payment['id']
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def gerar_mensalidades_lote(self, request):
        """Gera mensalidades em lote para turma ou escola"""
        escola_id = request.data.get('escola_id')
        turma_id = request.data.get('turma_id')
        competencia = request.data.get('competencia')
        valor_base = Decimal(request.data.get('valor_base', 0))

        if not escola_id or not competencia or valor_base <= 0:
            return Response({
                'success': False,
                'message': 'escola_id, competencia e valor_base são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Busca alunos
        alunos = Aluno.objects.filter(status='ATIVO', escola_id=escola_id)

        if turma_id:
            alunos = alunos.filter(turma_atual_id=turma_id)

        mensalidades_criadas = []
        erros = []

        try:
            escola = Escola.objects.get(id=escola_id)
            asaas = AsaasService(escola.asaas_api_key) if escola.asaas_api_key else None
        except Escola.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Escola não encontrada'
            }, status=status.HTTP_404_NOT_FOUND)

        for aluno in alunos:
            try:
                # Busca responsável financeiro
                responsavel_financeiro = aluno.responsaveis.filter(
                    alunoresponsavel__responsavel_financeiro=True
                ).first()

                if not responsavel_financeiro:
                    erros.append(f"Aluno {aluno.usuario.get_full_name()} sem responsável financeiro")
                    continue

                # Verifica se já existe mensalidade para esta competência
                if Mensalidade.objects.filter(
                        aluno=aluno,
                        competencia=competencia
                ).exists():
                    erros.append(f"Mensalidade já existe para {aluno.usuario.get_full_name()}")
                    continue

                # Cria mensalidade
                from datetime import datetime
                comp_date = datetime.strptime(competencia, '%Y-%m-%d').date()
                vencimento = comp_date.replace(day=10)

                mensalidade = Mensalidade.objects.create(
                    aluno=aluno,
                    responsavel_financeiro=responsavel_financeiro.responsavel_profile,
                    competencia=comp_date,
                    valor=valor_base,
                    valor_final=valor_base,
                    data_vencimento=vencimento,
                    status='PENDENTE'
                )

                # Gera boleto se integração configurada
                if asaas:
                    try:
                        asaas.gerar_cobranca(mensalidade)
                    except Exception as e:
                        erros.append(f"Erro ao gerar boleto para {aluno.usuario.get_full_name()}: {str(e)}")

                mensalidades_criadas.append(str(mensalidade.id))

            except Exception as e:
                erros.append(f"Erro ao processar {aluno.usuario.get_full_name()}: {str(e)}")

        return Response({
            'success': True,
            'mensalidades_criadas': len(mensalidades_criadas),
            'total_alunos': alunos.count(),
            'erros': erros,
            'ids': mensalidades_criadas
        })
