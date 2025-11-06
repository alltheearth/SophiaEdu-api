# webhooks/asaas_webhook.py

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