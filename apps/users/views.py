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

# Imports dos modelos
from .models import (
    User, Escola, EscolaUsuario, Professor, Aluno, Responsavel,
    AlunoResponsavel, AnoLetivo, Turma, Disciplina, TurmaDisciplina,
    PeriodoAvaliativo, Nota, Frequencia, Mensalidade, Aviso,
    Mensagem, AtividadeAgenda, Evento, TokenRedefinicaoSenha,
    HistoricoLogin, SessaoUsuario
)

# Imports dos serializers
from .serializers import (
    UserSerializer, UserCreateSerializer, EscolaSerializer,
    ProfessorSerializer, ProfessorListSerializer, AlunoSerializer,
    AlunoListSerializer, ResponsavelSerializer, TurmaSerializer,
    DisciplinaSerializer, NotaSerializer, FrequenciaSerializer,
    MensalidadeSerializer, AvisoSerializer, MensagemSerializer,
    AtividadeAgendaSerializer, EventoSerializer, AnoLetivoSerializer,
    DashboardSerializer
)

# Imports das permissões
from .permissions import (
    IsSuperUser, IsGestorOrAbove, IsCoordenadorOrAbove,
    IsProfessorOrAbove, CanEditNota, CanAccessAlunoData
)

# Imports dos serviços
from .services.asaas_service import AsaasService

# Imports dos filtros customizados
from .filters import (
    TurmaFilter, AlunoFilter, NotaFilter,
    FrequenciaFilter, MensalidadeFilter
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


# ============================================
# VIEWSETS - GESTÃO
# ============================================

class EscolaViewSet(viewsets.ModelViewSet):
    """CRUD de Escolas"""
    queryset = Escola.objects.all()
    serializer_class = EscolaSerializer
    permission_classes = [IsSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo', 'plano']
    search_fields = ['nome', 'cnpj']


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

        # ✅ CORRIGIDO: Pegar IDs das escolas
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


# ============================================
# VIEWSETS - ACADÊMICO
# ============================================

class AnoLetivoViewSet(viewsets.ModelViewSet):
    """CRUD de Anos Letivos"""
    queryset = AnoLetivo.objects.all()
    serializer_class = AnoLetivoSerializer
    permission_classes = [IsGestorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['escola', 'ativo']
    ordering_fields = ['ano']


class TurmaViewSet(viewsets.ModelViewSet):
    """CRUD de Turmas"""
    queryset = Turma.objects.all()
    serializer_class = TurmaSerializer
    permission_classes = [IsCoordenadorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['escola', 'ano_letivo', 'turno', 'serie']
    search_fields = ['nome', 'serie']
    ordering_fields = ['nome']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPERUSER':
            return self.queryset

        # ✅ CORRIGIDO: Pegar IDs das escolas
        escola_ids = user.escolas.values_list('escola_id', flat=True)
        return self.queryset.filter(escola_id__in=escola_ids)

    @action(detail=True, methods=['get'])
    def alunos(self, request, pk=None):
        """Lista alunos da turma"""
        turma = self.get_object()
        alunos = turma.alunos.select_related('usuario').all()
        serializer = AlunoListSerializer(alunos, many=True)
        return Response({'success': True, 'alunos': serializer.data})


class DisciplinaViewSet(viewsets.ModelViewSet):
    """CRUD de Disciplinas"""
    queryset = Disciplina.objects.all()
    serializer_class = DisciplinaSerializer
    permission_classes = [IsCoordenadorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['escola']
    search_fields = ['nome', 'codigo']


class ProfessorViewSet(viewsets.ModelViewSet):
    """CRUD de Professores"""
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer
    permission_classes = [IsGestorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['escola', 'status', 'turno']
    search_fields = ['usuario__first_name', 'usuario__last_name']
    ordering_fields = ['usuario__first_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProfessorListSerializer
        return ProfessorSerializer


class AlunoViewSet(viewsets.ModelViewSet):
    """CRUD de Alunos"""
    queryset = Aluno.objects.all()
    serializer_class = AlunoSerializer
    permission_classes = [IsProfessorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['escola', 'turma_atual', 'status']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'matricula']
    ordering_fields = ['usuario__first_name', 'matricula']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'SUPERUSER':
            return queryset

        if user.role in ['GESTOR', 'COORDENADOR']:
            # ✅ CORRIGIDO: Pegar IDs das escolas
            escola_ids = user.escolas.values_list('escola_id', flat=True)
            return queryset.filter(escola_id__in=escola_ids)

        if user.role == 'PROFESSOR':
            turmas = user.disciplinas_lecionadas.values_list('turma', flat=True)
            return queryset.filter(turma_atual__in=turmas)

        if user.role == 'RESPONSAVEL':
            return user.responsavel_profile.alunos.all()

        return queryset.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return AlunoListSerializer
        return AlunoSerializer

    @action(detail=True, methods=['get'])
    def boletim_completo(self, request, pk=None):
        """Boletim completo do aluno"""
        aluno = self.get_object()
        ano_letivo_id = request.query_params.get('ano_letivo_id')

        notas = Nota.objects.filter(
            aluno=aluno,
            periodo__ano_letivo_id=ano_letivo_id
        ).select_related('turma_disciplina__disciplina', 'periodo')

        boletim = {}
        for nota in notas:
            disc = nota.turma_disciplina.disciplina.nome
            periodo = nota.periodo.nome

            if disc not in boletim:
                boletim[disc] = {}
            if periodo not in boletim[disc]:
                boletim[disc][periodo] = []

            boletim[disc][periodo].append(float(nota.nota))

        return Response({'success': True, 'boletim': boletim})


class ResponsavelViewSet(viewsets.ModelViewSet):
    """CRUD de Responsáveis"""
    queryset = Responsavel.objects.select_related('usuario').all()
    serializer_class = ResponsavelSerializer
    permission_classes = [IsGestorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['usuario__first_name', 'usuario__last_name', 'cpf']


# ============================================
# VIEWSETS - NOTAS E FREQUÊNCIA
# ============================================

class NotaViewSet(viewsets.ModelViewSet):
    """CRUD de Notas"""
    queryset = Nota.objects.select_related(
        'aluno', 'turma_disciplina', 'periodo'
    ).all()
    serializer_class = NotaSerializer
    permission_classes = [IsProfessorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['aluno', 'turma_disciplina', 'periodo', 'tipo_avaliacao']
    ordering_fields = ['data_avaliacao', 'nota']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'SUPERUSER':
            return queryset

        if user.role == 'GESTOR':
            escola_ids = user.escolas.values_list('escola_id', flat=True)
            return queryset.filter(aluno__escola_id__in=escola_ids)

        if user.role == 'COORDENADOR':
            return queryset.filter(aluno__turma_atual__coordenador=user)

        if user.role == 'PROFESSOR':
            return queryset.filter(turma_disciplina__professor=user)

        if user.role == 'RESPONSAVEL':
            alunos = user.responsavel_profile.alunos.all()
            return queryset.filter(aluno__in=alunos)

        return queryset.none()

    @action(detail=False, methods=['get'])
    def boletim(self, request):
        """Boletim do aluno"""
        aluno_id = request.query_params.get('aluno_id')
        periodo_id = request.query_params.get('periodo_id')

        if not aluno_id or not periodo_id:
            return Response({
                'success': False,
                'message': 'aluno_id e periodo_id obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)

        notas = self.queryset.filter(aluno_id=aluno_id, periodo_id=periodo_id)

        boletim = {}
        for nota in notas:
            disc = nota.turma_disciplina.disciplina.nome
            if disc not in boletim:
                boletim[disc] = []
            boletim[disc].append(float(nota.nota))

        resultado = {
            disc: {
                'notas': notas_list,
                'media': sum(notas_list) / len(notas_list),
                'quantidade': len(notas_list)
            }
            for disc, notas_list in boletim.items()
        }

        return Response({'success': True, 'boletim': resultado})


class FrequenciaViewSet(viewsets.ModelViewSet):
    """CRUD de Frequência"""
    queryset = Frequencia.objects.select_related('aluno', 'turma_disciplina').all()
    serializer_class = FrequenciaSerializer
    permission_classes = [IsProfessorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['aluno', 'turma_disciplina', 'data', 'presente']
    ordering_fields = ['data']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['PROFESSOR']:
            return self.queryset.filter(turma_disciplina__professor=user)
        if user.role == 'RESPONSAVEL':
            alunos = user.responsavel_profile.alunos.all()
            return self.queryset.filter(aluno__in=alunos)
        return self.queryset

    @action(detail=False, methods=['post'])
    def registrar_chamada(self, request):
        """Registra chamada de toda turma"""
        turma_disciplina_id = request.data.get('turma_disciplina_id')
        data = request.data.get('data')
        presencas = request.data.get('presencas')  # [{aluno_id: true/false}]

        frequencias_criadas = []
        for item in presencas:
            freq, created = Frequencia.objects.update_or_create(
                aluno_id=item['aluno_id'],
                turma_disciplina_id=turma_disciplina_id,
                data=data,
                defaults={
                    'presente': item['presente'],
                    'lancado_por': request.user
                }
            )
            frequencias_criadas.append(freq.id)

        return Response({
            'success': True,
            'frequencias_registradas': len(frequencias_criadas)
        })


# ============================================
# VIEWSETS - FINANCEIRO
# ============================================

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
        user = self.request.user
        if user.role == 'SUPERUSER':
            return self.queryset
        if user.role == 'GESTOR':
            escola_ids = user.escolas.values_list('escola_id', flat=True)
            return self.queryset.filter(aluno__escola_id__in=escola_ids)
        if user.role == 'RESPONSAVEL':
            return self.queryset.filter(responsavel_financeiro=user.responsavel_profile)
        return self.queryset.none()

    @action(detail=True, methods=['post'])
    def gerar_boleto(self, request, pk=None):
        """Gera boleto"""
        mensalidade = self.get_object()
        escola = mensalidade.aluno.escola

        if not escola.asaas_api_key:
            return Response({
                'success': False,
                'message': 'Integração Asaas não configurada'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            asaas = AsaasService(escola.asaas_api_key)
            payment = asaas.gerar_cobranca(mensalidade)
            return Response({'success': True, 'payment': payment})
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def gerar_lote(self, request):
        """Gera mensalidades em lote"""
        escola_id = request.data.get('escola_id')
        turma_id = request.data.get('turma_id')
        competencia = request.data.get('competencia')
        valor_base = Decimal(request.data.get('valor_base', 0))

        alunos = Aluno.objects.filter(status='ATIVO', escola_id=escola_id)
        if turma_id:
            alunos = alunos.filter(turma_atual_id=turma_id)

        criadas = 0
        erros = []

        for aluno in alunos:
            resp_fin = aluno.responsaveis.filter(
                alunoresponsavel__responsavel_financeiro=True
            ).first()

            if not resp_fin:
                erros.append(f"{aluno.usuario.get_full_name()} sem responsável")
                continue

            from datetime import datetime
            comp_date = datetime.strptime(competencia, '%Y-%m-%d').date()

            _, created = Mensalidade.objects.get_or_create(
                aluno=aluno,
                competencia=comp_date,
                defaults={
                    'responsavel_financeiro': resp_fin.responsavel_profile,
                    'valor': valor_base,
                    'valor_final': valor_base,
                    'data_vencimento': comp_date.replace(day=10),
                    'status': 'PENDENTE'
                }
            )
            if created:
                criadas += 1

        return Response({
            'success': True,
            'criadas': criadas,
            'erros': erros
        })


# ============================================
# VIEWSETS - COMUNICAÇÃO
# ============================================

class AvisoViewSet(viewsets.ModelViewSet):
    """CRUD de Avisos"""
    queryset = Aviso.objects.select_related('escola', 'autor').prefetch_related('turmas').all()
    serializer_class = AvisoSerializer
    permission_classes = [IsCoordenadorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['escola', 'enviar_para_todos']
    ordering_fields = ['-criado_em']

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)


class MensagemViewSet(viewsets.ModelViewSet):
    """CRUD de Mensagens"""
    queryset = Mensagem.objects.select_related('remetente', 'destinatario').all()
    serializer_class = MensagemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['lida']
    ordering_fields = ['enviada_em']

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            Q(remetente=user) | Q(destinatario=user)
        )

    @action(detail=False, methods=['get'])
    def caixa_entrada(self, request):
        """Mensagens recebidas"""
        mensagens = self.queryset.filter(destinatario=request.user)
        serializer = self.get_serializer(mensagens, many=True)
        return Response({'success': True, 'mensagens': serializer.data})

    @action(detail=False, methods=['get'])
    def enviadas(self, request):
        """Mensagens enviadas"""
        mensagens = self.queryset.filter(remetente=request.user)
        serializer = self.get_serializer(mensagens, many=True)
        return Response({'success': True, 'mensagens': serializer.data})


# ============================================
# VIEWSETS - AGENDA E EVENTOS
# ============================================

class AtividadeAgendaViewSet(viewsets.ModelViewSet):
    """CRUD de Atividades"""
    queryset = AtividadeAgenda.objects.select_related(
        'turma_disciplina', 'professor'
    ).all()
    serializer_class = AtividadeAgendaSerializer
    permission_classes = [IsProfessorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['turma_disciplina', 'tipo']
    ordering_fields = ['data_entrega']

    def perform_create(self, serializer):
        serializer.save(professor=self.request.user)


class EventoViewSet(viewsets.ModelViewSet):
    """CRUD de Eventos"""
    queryset = Evento.objects.select_related('escola', 'responsavel').all()
    serializer_class = EventoSerializer
    permission_classes = [IsCoordenadorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['escola', 'tipo', 'status']
    ordering_fields = ['data']

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Confirma evento"""
        evento = self.get_object()
        evento.status = 'CONFIRMADO'
        evento.save()
        return Response({'success': True, 'message': 'Evento confirmado'})


# ============================================
# VIEWSETS - DASHBOARD
# ============================================

class DashboardViewSet(viewsets.ViewSet):
    """Dashboard com estatísticas"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def geral(self, request):
        """Dashboard geral"""
        user = request.user
        escola_id = request.query_params.get('escola_id')

        if not escola_id:
            return Response({
                'success': False,
                'message': 'escola_id obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Total de alunos
        total_alunos = Aluno.objects.filter(
            escola_id=escola_id,
            status='ATIVO'
        ).count()

        # Total de professores
        total_professores = Professor.objects.filter(
            escola_id=escola_id,
            status='ATIVO'
        ).count()

        # Total de turmas
        total_turmas = Turma.objects.filter(
            escola_id=escola_id
        ).count()

        # Mensalidades pendentes
        mensalidades_pendentes = Mensalidade.objects.filter(
            aluno__escola_id=escola_id,
            status='PENDENTE'
        ).aggregate(
            total=Sum('valor_final'),
            quantidade=Count('id')
        )

        # Mensalidades atrasadas
        mensalidades_atrasadas = Mensalidade.objects.filter(
            aluno__escola_id=escola_id,
            status='ATRASADO'
        ).aggregate(
            total=Sum('valor_final'),
            quantidade=Count('id')
        )

        return Response({
            'success': True,
            'data': {
                'total_alunos': total_alunos,
                'total_professores': total_professores,
                'total_turmas': total_turmas,
                'mensalidades_pendentes': mensalidades_pendentes,
                'mensalidades_atrasadas': mensalidades_atrasadas
            }
        })

    @action(detail=False, methods=['get'])
    def financeiro(self, request):
        """Dashboard financeiro"""
        escola_id = request.query_params.get('escola_id')

        # Receita por status
        receita = Mensalidade.objects.filter(
            aluno__escola_id=escola_id
        ).values('status').annotate(
            total=Sum('valor_final'),
            quantidade=Count('id')
        )

        return Response({
            'success': True,
            'receita_por_status': list(receita)
        })


# ============================================
# VIEWSETS - LEADS (CRM)
# ============================================

class LeadViewSet(viewsets.ModelViewSet):
    """CRUD de Leads - Simples"""
    queryset = User.objects.filter(role='ALUNO', ativo=False)
    serializer_class = UserSerializer
    permission_classes = [IsGestorOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['created_at']


# ============================================
# VIEWSETS - CONTATOS E FAQ
# ============================================

class ContatoViewSet(viewsets.ViewSet):
    """Endpoint simples de contato"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def enviar(self, request):
        """Envia mensagem de contato"""
        nome = request.data.get('nome')
        email = request.data.get('email')
        mensagem = request.data.get('mensagem')

        # TODO: Implementar envio de email

        return Response({
            'success': True,
            'message': 'Mensagem enviada com sucesso'
        })


class FAQViewSet(viewsets.ViewSet):
    """FAQ simples"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def listar(self, request):
        """Lista FAQs"""
        faqs = [
            {
                'id': 1,
                'pergunta': 'Como faço para acessar o sistema?',
                'resposta': 'Use seu CPF e senha fornecidos pela escola.'
            },
            {
                'id': 2,
                'pergunta': 'Como vejo as notas do meu filho?',
                'resposta': 'Acesse o menu Boletim após fazer login.'
            },
            {
                'id': 3,
                'pergunta': 'Como pago a mensalidade?',
                'resposta': 'Acesse Financeiro e gere o boleto ou PIX.'
            }
        ]
        return Response({'success': True, 'faqs': faqs})


class DocumentoViewSet(viewsets.ViewSet):
    """Documentos simples"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def listar(self, request):
        """Lista documentos disponíveis"""
        documentos = [
            {
                'id': 1,
                'titulo': 'Contrato de Matrícula',
                'tipo': 'PDF',
                'url': '/media/documentos/contrato.pdf'
            },
            {
                'id': 2,
                'titulo': 'Calendário Escolar',
                'tipo': 'PDF',
                'url': '/media/documentos/calendario.pdf'
            }
        ]
        return Response({'success': True, 'documentos': documentos})


# sophia/views.py - ADICIONAR AO ARQUIVO EXISTENTE

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.db import transaction

from .models import (
    CanalComunicacao, ParticipanteCanal, MensagemCanal,
    AnexoMensagem, ResponsavelConversa, NotificacaoComunicacao,
    AuditoriaConversa
)
from .serializers import (
    CanalComunicacaoSerializer, CanalComunicacaoListSerializer,
    MensagemCanalSerializer, ParticipanteCanalSerializer,
    ResponsavelConversaSerializer, NotificacaoComunicacaoSerializer,
    AuditoriaConversaSerializer, CriarCanalSerializer,
    EnviarMensagemSerializer, AdicionarParticipantesSerializer,
    AssumirConversaSerializer
)
from .utils.supabase_storage import upload_file


# ============================================
# VIEWSETS - COMUNICAÇÃO
# ============================================

class CanalComunicacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para canais de comunicação
    Implementa hierarquia de acesso e visibilidade
    """
    queryset = CanalComunicacao.objects.select_related(
        'escola', 'criado_por', 'turma', 'disciplina'
    ).prefetch_related(
        'participantes__usuario',
        'responsaveis'
    ).all()
    serializer_class = CanalComunicacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return CanalComunicacaoListSerializer
        return CanalComunicacaoSerializer

    def get_queryset(self):
        """
        Filtra canais baseado no papel do usuário
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Superuser e Gestor veem tudo
        if user.role in ['SUPERUSER', 'GESTOR']:
            escola_id = self.request.query_params.get('escola')
            if escola_id:
                queryset = queryset.filter(escola_id=escola_id)
            return queryset

        # Coordenador vê canais visíveis para coordenação
        if user.role == 'COORDENADOR':
            # Canais das suas turmas + canais onde é participante
            turmas_coordenadas = user.turmas_coordenadas.values_list('id', flat=True)
            queryset = queryset.filter(
                Q(visivel_para_coordenacao=True, turma__in=turmas_coordenadas) |
                Q(participantes__usuario=user, participantes__ativo=True)
            ).distinct()
            return queryset

        # Professor, Responsável, Aluno: apenas canais onde participa
        return queryset.filter(
            participantes__usuario=user,
            participantes__ativo=True
        ).distinct()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Cria novo canal"""
        serializer = CriarCanalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validações
        if data['tipo'] == 'INDIVIDUAL' and len(data.get('participantes_ids', [])) != 1:
            return Response({
                'success': False,
                'message': 'Canal individual deve ter exatamente 1 outro participante'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verifica se já existe canal individual entre os usuários
        if data['tipo'] == 'INDIVIDUAL':
            outro_usuario_id = data['participantes_ids'][0]
            canal_existente = CanalComunicacao.objects.filter(
                tipo='INDIVIDUAL',
                participantes__usuario=request.user
            ).filter(
                participantes__usuario_id=outro_usuario_id
            ).first()

            if canal_existente:
                return Response({
                    'success': True,
                    'message': 'Canal já existe',
                    'canal': CanalComunicacaoSerializer(canal_existente, context={'request': request}).data
                })

        # Criar canal
        escola_id = request.data.get('escola') or request.user.escolas.first().escola_id

        canal = CanalComunicacao.objects.create(
            escola_id=escola_id,
            tipo=data['tipo'],
            nome=data.get('nome', ''),
            descricao=data.get('descricao', ''),
            turma_id=data.get('turma'),
            disciplina_id=data.get('disciplina'),
            criado_por=request.user,
            visivel_para_coordenacao=data.get('visivel_para_coordenacao', True),
            permite_anexos=data.get('permite_anexos', True),
            permite_entrega_trabalhos=data.get('permite_entrega_trabalhos', False)
        )

        # Adicionar criador como admin
        ParticipanteCanal.objects.create(
            canal=canal,
            usuario=request.user,
            papel='ADMIN',
            adicionado_por=request.user
        )

        # Adicionar outros participantes
        for usuario_id in data.get('participantes_ids', []):
            ParticipanteCanal.objects.create(
                canal=canal,
                usuario_id=usuario_id,
                papel='MEMBRO',
                adicionado_por=request.user
            )

        # Criar responsável se for canal com professor
        if request.user.role == 'PROFESSOR' or any(
                User.objects.get(id=uid).role == 'PROFESSOR'
                for uid in data.get('participantes_ids', [])
        ):
            professor = request.user if request.user.role == 'PROFESSOR' else User.objects.get(
                id__in=data.get('participantes_ids', []),
                role='PROFESSOR'
            )
            ResponsavelConversa.objects.create(
                canal=canal,
                responsavel_original=professor
            )

        # Auditoria
        AuditoriaConversa.objects.create(
            usuario=request.user,
            acao='CANAL_CRIADO',
            canal=canal,
            detalhes={'tipo': data['tipo'], 'nome': data.get('nome')},
            ip_address=self.get_client_ip(request)
        )

        return Response({
            'success': True,
            'canal': CanalComunicacaoSerializer(canal, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def enviar_mensagem(self, request, pk=None):
        """Envia mensagem no canal"""
        canal = self.get_object()

        # Verifica permissão
        if not canal.pode_enviar_mensagem(request.user):
            return Response({
                'success': False,
                'message': 'Você não tem permissão para enviar mensagens neste canal'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = EnviarMensagemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Criar mensagem
        mensagem = MensagemCanal.objects.create(
            canal=canal,
            remetente=request.user,
            tipo=data['tipo'],
            conteudo=data['conteudo'],
            prioridade=data.get('prioridade', 'NORMAL'),
            respondendo_a_id=data.get('respondendo_a'),
            requer_confirmacao=data.get('requer_confirmacao', False),
            ip_remetente=self.get_client_ip(request)
        )

        # Processar anexos
        anexos_data = data.get('anexos', [])
        for anexo_data in anexos_data:
            AnexoMensagem.objects.create(
                mensagem=mensagem,
                tipo=anexo_data['tipo'],
                nome_arquivo=anexo_data['nome_arquivo'],
                url=anexo_data['url'],
                tamanho=anexo_data['tamanho'],
                mime_type=anexo_data['mime_type'],
                e_trabalho=anexo_data.get('e_trabalho', False),
                atividade_id=anexo_data.get('atividade_id')
            )

        # Atualizar timestamp do canal
        canal.ultima_mensagem_em = timezone.now()
        canal.save()

        # Criar notificações para participantes
        participantes = canal.participantes.filter(ativo=True).exclude(usuario=request.user)
        for participante in participantes:
            if participante.notificar:
                NotificacaoComunicacao.objects.create(
                    usuario=participante.usuario,
                    tipo='NOVA_MENSAGEM',
                    canal=canal,
                    mensagem=mensagem,
                    titulo=f"Nova mensagem de {request.user.get_full_name()}",
                    conteudo=data['conteudo'][:200]
                )

        # Auditoria
        AuditoriaConversa.objects.create(
            usuario=request.user,
            acao='MENSAGEM_ENVIADA',
            canal=canal,
            mensagem=mensagem,
            detalhes={'tipo': data['tipo'], 'prioridade': data.get('prioridade')},
            ip_address=self.get_client_ip(request)
        )

        return Response({
            'success': True,
            'mensagem': MensagemCanalSerializer(mensagem, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def mensagens(self, request, pk=None):
        """Lista mensagens do canal com paginação"""
        canal = self.get_object()

        # Verifica permissão
        if not canal.pode_visualizar(request.user):
            return Response({
                'success': False,
                'message': 'Você não tem permissão para visualizar este canal'
            }, status=status.HTTP_403_FORBIDDEN)

        # Paginação
        pagina = int(request.query_params.get('pagina', 1))
        por_pagina = int(request.query_params.get('por_pagina', 50))
        inicio = (pagina - 1) * por_pagina
        fim = inicio + por_pagina

        mensagens = canal.mensagens.filter(excluida=False).select_related(
            'remetente'
        ).prefetch_related(
            'anexos', 'respostas'
        ).order_by('-enviada_em')[inicio:fim]

        serializer = MensagemCanalSerializer(mensagens, many=True, context={'request': request})

        # Marcar como lidas
        canal.marcar_como_lida(request.user)

        return Response({
            'success': True,
            'mensagens': serializer.data,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total': canal.mensagens.filter(excluida=False).count()
        })

    @action(detail=True, methods=['post'])
    def adicionar_participantes(self, request, pk=None):
        """Adiciona participantes ao canal"""
        canal = self.get_object()

        # Apenas admin ou gestor/coordenador
        if not (canal.administradores.filter(id=request.user.id).exists() or
                request.user.role in ['SUPERUSER', 'GESTOR', 'COORDENADOR']):
            return Response({
                'success': False,
                'message': 'Você não tem permissão para adicionar participantes'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = AdicionarParticipantesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        adicionados = []
        for usuario_id in data['usuarios_ids']:
            participante, created = ParticipanteCanal.objects.get_or_create(
                canal=canal,
                usuario_id=usuario_id,
                defaults={
                    'papel': data['papel'],
                    'adicionado_por': request.user,
                    'notificar': data['notificar']
                }
            )
            if created:
                adicionados.append(participante)

                # Notificar novo participante
                if data['notificar']:
                    NotificacaoComunicacao.objects.create(
                        usuario_id=usuario_id,
                        tipo='CANAL_CRIADO',
                        canal=canal,
                        titulo=f"Você foi adicionado ao canal {canal.nome}",
                        conteudo=f"Por {request.user.get_full_name()}"
                    )

                # Auditoria
                AuditoriaConversa.objects.create(
                    usuario=request.user,
                    acao='PARTICIPANTE_ADICIONADO',
                    canal=canal,
                    detalhes={'usuario_adicionado_id': str(usuario_id)},
                    ip_address=self.get_client_ip(request)
                )

        return Response({
            'success': True,
            'message': f'{len(adicionados)} participante(s) adicionado(s)',
            'participantes': ParticipanteCanalSerializer(adicionados, many=True).data
        })

    @action(detail=True, methods=['post'])
    def marcar_como_lida(self, request, pk=None):
        """Marca todas as mensagens como lidas"""
        canal = self.get_object()
        canal.marcar_como_lida(request.user)

        return Response({
            'success': True,
            'message': 'Mensagens marcadas como lidas'
        })

    @action(detail=True, methods=['post'])
    def assumir_conversa(self, request, pk=None):
        """Coordenador/Gestor assume responsabilidade pela conversa"""
        canal = self.get_object()

        # Apenas Coordenador ou Gestor
        if request.user.role not in ['COORDENADOR', 'GESTOR', 'SUPERUSER']:
            return Response({
                'success': False,
                'message': 'Apenas coordenadores e gestores podem assumir conversas'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = AssumirConversaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        responsavel = canal.responsaveis.filter(ativo=True).first()
        if not responsavel:
            return Response({
                'success': False,
                'message': 'Canal não possui responsável definido'
            }, status=status.HTTP_400_BAD_REQUEST)

        responsavel.assumir(request.user, serializer.validated_data.get('motivo', ''))

        # Notificar responsável original
        NotificacaoComunicacao.objects.create(
            usuario=responsavel.responsavel_original,
            tipo='CONVERSA_ASSUMIDA',
            canal=canal,
            titulo='Conversa assumida',
            conteudo=f'{request.user.get_full_name()} assumiu a conversa'
        )

        # Auditoria
        AuditoriaConversa.objects.create(
            usuario=request.user,
            acao='CONVERSA_ASSUMIDA',
            canal=canal,
            detalhes={
                'responsavel_original_id': str(responsavel.responsavel_original_id),
                'motivo': serializer.validated_data.get('motivo', '')
            },
            ip_address=self.get_client_ip(request)
        )

        return Response({
            'success': True,
            'message': 'Conversa assumida com sucesso',
            'responsavel': ResponsavelConversaSerializer(responsavel).data
        })

    @action(detail=True, methods=['post'])
    def devolver_conversa(self, request, pk=None):
        """Devolve conversa ao responsável original"""
        canal = self.get_object()

        responsavel = canal.responsaveis.filter(ativo=True, assumida_por=request.user).first()
        if not responsavel:
            return Response({
                'success': False,
                'message': 'Você não assumiu esta conversa'
            }, status=status.HTTP_400_BAD_REQUEST)

        responsavel.devolver()

        # Notificar responsável original
        NotificacaoComunicacao.objects.create(
            usuario=responsavel.responsavel_original,
            tipo='CONVERSA_ASSUMIDA',  # Reutiliza tipo
            canal=canal,
            titulo='Conversa devolvida',
            conteudo=f'{request.user.get_full_name()} devolveu a conversa'
        )

        # Auditoria
        AuditoriaConversa.objects.create(
            usuario=request.user,
            acao='CONVERSA_DEVOLVIDA',
            canal=canal,
            detalhes={'responsavel_original_id': str(responsavel.responsavel_original_id)},
            ip_address=self.get_client_ip(request)
        )

        return Response({
            'success': True,
            'message': 'Conversa devolvida ao responsável original'
        })

    @action(detail=False, methods=['get'])
    def meus_canais(self, request):
        """Lista canais do usuário com estatísticas"""
        canais = self.get_queryset().annotate(
            total_nao_lidas=Count(
                'mensagens',
                filter=Q(mensagens__lida=False) & ~Q(mensagens__remetente=request.user)
            )
        )

        # Filtros
        tipo = request.query_params.get('tipo')
        if tipo:
            canais = canais.filter(tipo=tipo)

        status_filter = request.query_params.get('status')
        if status_filter:
            canais = canais.filter(status=status_filter)

        serializer = self.get_serializer(canais, many=True)

        return Response({
            'success': True,
            'canais': serializer.data,
            'total': canais.count()
        })

    @action(detail=False, methods=['get'])
    def conversas_pendentes(self, request):
        """Lista conversas que precisam de resposta (para coordenadores/gestores)"""
        if request.user.role not in ['COORDENADOR', 'GESTOR', 'SUPERUSER']:
            return Response({
                'success': False,
                'message': 'Acesso negado'
            }, status=status.HTTP_403_FORBIDDEN)

        # Conversas com SLA vencido ou próximo
        from datetime import timedelta
        limite = timezone.now() - timedelta(hours=20)

        canais_pendentes = self.get_queryset().filter(
            responsaveis__atrasado=True
        ).distinct()

        serializer = CanalComunicacaoListSerializer(canais_pendentes, many=True, context={'request': request})

        return Response({
            'success': True,
            'canais_pendentes': serializer.data,
            'total': canais_pendentes.count()
        })

    def get_client_ip(self, request):
        """Obtém IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MensagemCanalViewSet(viewsets.ModelViewSet):
    """ViewSet para mensagens"""
    queryset = MensagemCanal.objects.select_related('remetente', 'canal').all()
    serializer_class = MensagemCanalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra mensagens dos canais que o usuário tem acesso"""
        user = self.request.user

        if user.role in ['SUPERUSER', 'GESTOR']:
            return self.queryset

        # Mensagens dos canais onde participa ou pode ver
        canais_visiveis = CanalComunicacao.objects.filter(
            Q(participantes__usuario=user) |
            Q(visivel_para_coordenacao=True, turma__coordenador=user)
        ).distinct().values_list('id', flat=True)

        return self.queryset.filter(canal_id__in=canais_visiveis, excluida=False)

    @action(detail=True, methods=['put'])
    def editar(self, request, pk=None):
        """Edita mensagem"""
        mensagem = self.get_object()

        if not mensagem.pode_editar(request.user):
            return Response({
                'success': False,
                'message': 'Você não pode editar esta mensagem'
            }, status=status.HTTP_403_FORBIDDEN)

        novo_conteudo = request.data.get('conteudo')
        if not novo_conteudo:
            return Response({
                'success': False,
                'message': 'Conteúdo obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        mensagem.conteudo = novo_conteudo
        mensagem.editada = True
        mensagem.editada_em = timezone.now()
        mensagem.save()

        # Auditoria
        AuditoriaConversa.objects.create(
            usuario=request.user,
            acao='MENSAGEM_EDITADA',
            canal=mensagem.canal,
            mensagem=mensagem,
            detalhes={'conteudo_anterior': mensagem.conteudo}
        )

        return Response({
            'success': True,
            'mensagem': self.get_serializer(mensagem).data
        })

    @action(detail=True, methods=['delete'])
    def excluir(self, request, pk=None):
        """Exclui (soft delete) mensagem"""
        mensagem = self.get_object()

        if not mensagem.pode_excluir(request.user):
            return Response({
                'success': False,
                'message': 'Você não pode excluir esta mensagem'
            }, status=status.HTTP_403_FORBIDDEN)

        mensagem.excluida = True
        mensagem.excluida_em = timezone.now()
        mensagem.save()

        # Auditoria
        AuditoriaConversa.objects.create(
            usuario=request.user,
            acao='MENSAGEM_EXCLUIDA',
            canal=mensagem.canal,
            mensagem=mensagem,
            detalhes={'conteudo': mensagem.conteudo}
        )

        return Response({
            'success': True,
            'message': 'Mensagem excluída'
        })


class NotificacaoComunicacaoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para notificações"""
    queryset = NotificacaoComunicacao.objects.select_related('canal', 'mensagem').all()
    serializer_class = NotificacaoComunicacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(usuario=self.request.user)

    @action(detail=False, methods=['get'])
    def nao_lidas(self, request):
        """Lista notificações não lidas"""
        notificacoes = self.get_queryset().filter(lida=False).order_by('-criada_em')
        serializer = self.get_serializer(notificacoes, many=True)

        return Response({
            'success': True,
            'notificacoes': serializer.data,
            'total': notificacoes.count()
        })

    @action(detail=True, methods=['post'])
    def marcar_lida(self, request, pk=None):
        """Marca notificação como lida"""
        notificacao = self.get_object()
        notificacao.marcar_como_lida()

        return Response({
            'success': True,
            'message': 'Notificação marcada como lida'
        })

    @action(detail=False, methods=['post'])
    def marcar_todas_lidas(self, request):
        """Marca todas como lidas"""
        self.get_queryset().filter(lida=False).update(
            lida=True,
            lida_em=timezone.now()
        )

        return Response({
            'success': True,
            'message': 'Todas as notificações foram marcadas como lidas'
        })


class AuditoriaConversaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para auditoria (apenas gestores)"""
    queryset = AuditoriaConversa.objects.select_related('usuario', 'canal').all()
    serializer_class = AuditoriaConversaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role not in ['SUPERUSER', 'GESTOR']:
            return self.queryset.none()

        return self.queryset.order_by('-criado_em')