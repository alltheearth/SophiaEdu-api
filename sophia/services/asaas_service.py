# services/asaas_service.py

import requests
from django.conf import settings
from decimal import Decimal


class AsaasService:
    """Serviço para integração com Asaas"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = settings.ASAAS_API_URL  # https://api.asaas.com/v3
        self.headers = {
            'access_token': self.api_key,
            'Content-Type': 'application/json'
        }

    def criar_cliente(self, responsavel):
        """Cria/atualiza cliente no Asaas"""
        data = {
            'name': responsavel.usuario.get_full_name(),
            'cpfCnpj': responsavel.cpf,
            'email': responsavel.usuario.email,
            'phone': responsavel.usuario.telefone,
            'mobilePhone': responsavel.usuario.telefone,
            'address': responsavel.endereco,
            'externalReference': str(responsavel.id)
        }

        response = requests.post(
            f'{self.base_url}/customers',
            json=data,
            headers=self.headers
        )

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Erro ao criar cliente: {response.text}")

    def gerar_cobranca(self, mensalidade):
        """Gera cobrança (boleto/PIX) no Asaas"""
        responsavel = mensalidade.responsavel_financeiro

        # Verifica se cliente existe no Asaas
        customer_id = self._get_or_create_customer(responsavel)

        data = {
            'customer': customer_id,
            'billingType': 'BOLETO',  # ou 'PIX', 'CREDIT_CARD'
            'value': float(mensalidade.valor_final),
            'dueDate': mensalidade.data_vencimento.strftime('%Y-%m-%d'),
            'description': f"Mensalidade {mensalidade.competencia.strftime('%m/%Y')} - {mensalidade.aluno.usuario.get_full_name()}",
            'externalReference': str(mensalidade.id),
            'postalService': False,  # Não enviar pelos Correios

            # Configurações de multa e juros
            'fine': {
                'value': 2.00,  # 2%
                'type': 'PERCENTAGE'
            },
            'interest': {
                'value': 1.00,  # 1% ao mês
                'type': 'PERCENTAGE'
            },

            # Desconto para pagamento antecipado
            'discount': {
                'value': float(mensalidade.desconto) if mensalidade.desconto > 0 else 0,
                'dueDateLimitDays': 0,
                'type': 'FIXED'
            }
        }

        response = requests.post(
            f'{self.base_url}/payments',
            json=data,
            headers=self.headers
        )

        if response.status_code in [200, 201]:
            payment_data = response.json()

            # Atualiza mensalidade com dados do Asaas
            mensalidade.asaas_payment_id = payment_data['id']
            mensalidade.boleto_url = payment_data.get('bankSlipUrl', '')

            # Gera PIX também
            if payment_data.get('pixTransaction'):
                mensalidade.pix_qrcode = payment_data['pixTransaction']['qrCode']['payload']

            mensalidade.save()

            return payment_data
        else:
            raise Exception(f"Erro ao gerar cobrança: {response.text}")

    def _get_or_create_customer(self, responsavel):
        """Busca ou cria cliente no Asaas"""
        # Busca por CPF
        response = requests.get(
            f'{self.base_url}/customers',
            params={'cpfCnpj': responsavel.cpf},
            headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()
            if data['totalCount'] > 0:
                return data['data'][0]['id']

        # Se não existe, cria
        customer = self.criar_cliente(responsavel)
        return customer['id']

    def verificar_pagamento(self, payment_id):
        """Verifica status de pagamento no Asaas"""
        response = requests.get(
            f'{self.base_url}/payments/{payment_id}',
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erro ao verificar pagamento: {response.text}")

    def cancelar_cobranca(self, payment_id):
        """Cancela cobrança no Asaas"""
        response = requests.delete(
            f'{self.base_url}/payments/{payment_id}',
            headers=self.headers
        )

        return response.status_code == 200