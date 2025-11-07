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
        escolas = user.escolas.values_list('escola_id', flat=True)
        return self.queryset.filter(escolas__escola_id__in=escolas)

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
        escolas = user.escolas.all()
        return self.queryset.filter(escola__in=escolas)

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
            escolas = user.escolas.all()
            return queryset.filter(escola__in=escolas)
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
            escolas = user.escolas.all()
            return queryset.filter(aluno__escola__in=escolas)
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
            escolas = user.escolas.all()
            return self.queryset.filter(aluno__escola__in=escolas)
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
