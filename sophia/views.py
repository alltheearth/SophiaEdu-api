# views.py

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Nota, Aluno, Turma
from .serializers import NotaSerializer, AlunoSerializer
from .permissions import IsProfessorOrAbove, CanEditNota, CanAccessAlunoData


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
            # Gestor vê todas as notas da sua escola
            escolas = user.escolas.all()
            return queryset.filter(aluno__escola__in=escolas)

        if user.role == 'COORDENADOR':
            # Coordenador vê notas das turmas que coordena
            return queryset.filter(aluno__turma_atual__coordenador=user)

        if user.role == 'PROFESSOR':
            # Professor vê apenas notas das disciplinas que leciona
            return queryset.filter(turma_disciplina__professor=user)

        if user.role == 'RESPONSAVEL':
            # Responsável vê apenas notas dos filhos
            responsavel = user.responsavel_profile
            alunos = responsavel.alunos.all()
            return queryset.filter(aluno__in=alunos)

        return queryset.none()

    @action(detail=False, methods=['get'])
    def boletim(self, request):
        """Endpoint para gerar boletim do aluno"""
        aluno_id = request.query_params.get('aluno_id')
        periodo_id = request.query_params.get('periodo_id')

        # Verifica permissão de acesso ao aluno
        aluno = Aluno.objects.get(id=aluno_id)
        self.check_object_permissions(request, aluno)

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
                'notas': notas,
                'media': sum(notas) / len(notas)
            }
            for disciplina, notas in boletim.items()
        }

        return Response(resultado)


class AlunoViewSet(viewsets.ModelViewSet):
    """CRUD de Alunos"""
    queryset = Aluno.objects.select_related(
        'usuario', 'escola', 'turma_atual'
    ).prefetch_related('responsaveis').all()
    serializer_class = AlunoSerializer
    permission_classes = [IsProfessorOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['escola', 'turma_atual', 'status']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'matricula']

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
            # Professor vê alunos das suas turmas
            turmas = user.disciplinas_lecionadas.values_list('turma', flat=True)
            return queryset.filter(turma_atual__in=turmas)

        if user.role == 'RESPONSAVEL':
            # Responsável vê apenas seus filhos
            responsavel = user.responsavel_profile
            return responsavel.alunos.all()

        return queryset.none()


# views.py - Endpoint para gerar mensalidades

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .services.asaas_service import AsaasService


class MensalidadeViewSet(viewsets.ModelViewSet):
    queryset = Mensalidade.objects.all()
    serializer_class = MensalidadeSerializer
    permission_classes = [IsGestorOrAbove]

    @action(detail=True, methods=['post'])
    def gerar_boleto(self, request, pk=None):
        """Gera boleto para mensalidade"""
        mensalidade = self.get_object()
        escola = mensalidade.aluno.escola

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
        competencia = request.data.get('competencia')  # YYYY-MM-DD
        valor_base = Decimal(request.data.get('valor_base'))

        # Busca alunos
        alunos = Aluno.objects.filter(status='ATIVO')
        if turma_id:
            alunos = alunos.filter(turma_atual_id=turma_id)
        else:
            alunos = alunos.filter(escola_id=escola_id)

        mensalidades_criadas = []
        escola = Escola.objects.get(id=escola_id)
        asaas = AsaasService(escola.asaas_api_key)

        for aluno in alunos:
            # Busca responsável financeiro
            responsavel_financeiro = aluno.responsaveis.filter(
                alunoresponsavel__responsavel_financeiro=True
            ).first()

            if not responsavel_financeiro:
                continue

            # Cria mensalidade
            mensalidade = Mensalidade.objects.create(
                aluno=aluno,
                responsavel_financeiro=responsavel_financeiro.responsavel_profile,
                competencia=competencia,
                valor=valor_base,
                valor_final=valor_base,
                data_vencimento=competencia.replace(day=10),  # Vencimento dia 10
                status='PENDENTE'
            )

            # Gera boleto automaticamente
            try:
                asaas.gerar_cobranca(mensalidade)
                mensalidades_criadas.append(mensalidade.id)
            except Exception as e:
                print(f"Erro ao gerar boleto para {aluno.usuario.get_full_name()}: {e}")

        return Response({
            'success': True,
            'mensalidades_criadas': len(mensalidades_criadas),
            'ids': mensalidades_criadas
        })# webhooks/asaas_webhook.py

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from ..models import Mensalidade

@csrf_exempt
@require_POST
def asaas_webhook(request):
    """
    Webhook para receber notificações do Asaas
    Configurar no painel: https://www.asaas.com/config/webhook
    """
    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        payment = payload.get('payment')

        if not payment:
            return JsonResponse({'status': 'error', 'message': 'No payment data'}, status=400)

        payment_id = payment.get('id')

        # Busca mensalidade
        try:
            mensalidade = Mensalidade.objects.get(asaas_payment_id=payment_id)
        except Mensalidade.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Mensalidade não encontrada'}, status=404)

        # Processa eventos
        if event == 'PAYMENT_RECEIVED':
            # Pagamento confirmado
            mensalidade.status = 'PAGO'
            mensalidade.data_pagamento = payment.get('paymentDate')
            mensalidade.save()

            # TODO: Enviar email/notificação para responsável

        elif event == 'PAYMENT_OVERDUE':
            # Pagamento atrasado
            mensalidade.status = 'ATRASADO'
            mensalidade.save()

            # TODO: Enviar notificação de atraso

        elif event == 'PAYMENT_DELETED':
            # Cobrança cancelada
            mensalidade.status = 'CANCELADO'
            mensalidade.save()

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)