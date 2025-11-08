"""
Filtros customizados para APIs
"""
from django_filters import rest_framework as filters
from .models import Turma, Aluno, Nota, Frequencia, Mensalidade


class TurmaFilter(filters.FilterSet):
    """Filtro customizado para Turmas"""

    # Permite filtrar por ID (int) ou pelo ano (int)
    ano_letivo = filters.NumberFilter(method='filter_ano_letivo')
    ano = filters.NumberFilter(field_name='ano_letivo__ano')

    class Meta:
        model = Turma
        fields = {
            'escola': ['exact'],
            'turno': ['exact'],
            'serie': ['exact', 'icontains'],
            'nome': ['exact', 'icontains'],
        }

    def filter_ano_letivo(self, queryset, name, value):
        """
        Filtra por ano_letivo_id (int) ou por ano (int)

        Primeiro tenta filtrar pelo ano (ex: 2025)
        Se não encontrar, assume que é o ID do ano letivo

        Exemplos:
        - ?ano_letivo=2025 → Filtra por ano_letivo.ano=2025
        - ?ano_letivo=1    → Se não existir ano=1, filtra por ano_letivo.id=1
        """
        from .models import AnoLetivo

        # Tenta encontrar AnoLetivo pelo ano
        ano_letivo_obj = AnoLetivo.objects.filter(ano=value).first()

        if ano_letivo_obj:
            # Encontrou pelo ano, usa o ID
            return queryset.filter(ano_letivo_id=ano_letivo_obj.id)
        else:
            # Não encontrou pelo ano, assume que é o ID
            return queryset.filter(ano_letivo_id=value)


class AlunoFilter(filters.FilterSet):
    """Filtro customizado para Alunos"""

    # Filtros por relacionamentos
    turma = filters.CharFilter(field_name='turma_atual_id')
    ano_letivo = filters.NumberFilter(field_name='turma_atual__ano_letivo__ano')
    serie = filters.CharFilter(field_name='turma_atual__serie', lookup_expr='icontains')

    class Meta:
        model = Aluno
        fields = {
            'escola': ['exact'],
            'status': ['exact'],
            'matricula': ['exact', 'icontains'],
            'turma_atual': ['exact'],
        }


class NotaFilter(filters.FilterSet):
    """Filtro customizado para Notas"""

    # Filtros por relacionamentos
    disciplina = filters.CharFilter(field_name='turma_disciplina__disciplina_id')
    disciplina_nome = filters.CharFilter(field_name='turma_disciplina__disciplina__nome', lookup_expr='icontains')
    turma = filters.CharFilter(field_name='turma_disciplina__turma_id')
    ano_letivo = filters.NumberFilter(field_name='periodo__ano_letivo__ano')
    periodo_nome = filters.CharFilter(field_name='periodo__nome', lookup_expr='icontains')

    # Filtros por valores
    nota_min = filters.NumberFilter(field_name='nota', lookup_expr='gte')
    nota_max = filters.NumberFilter(field_name='nota', lookup_expr='lte')

    class Meta:
        model = Nota
        fields = {
            'aluno': ['exact'],
            'turma_disciplina': ['exact'],
            'periodo': ['exact'],
            'tipo_avaliacao': ['exact', 'icontains'],
            'data_avaliacao': ['exact', 'gte', 'lte'],
        }


class FrequenciaFilter(filters.FilterSet):
    """Filtro customizado para Frequências"""

    # Filtros por relacionamentos
    disciplina = filters.CharFilter(field_name='turma_disciplina__disciplina_id')
    turma = filters.CharFilter(field_name='turma_disciplina__turma_id')

    # Filtros por período
    data_inicio = filters.DateFilter(field_name='data', lookup_expr='gte')
    data_fim = filters.DateFilter(field_name='data', lookup_expr='lte')
    mes = filters.NumberFilter(field_name='data', lookup_expr='month')
    ano = filters.NumberFilter(field_name='data', lookup_expr='year')

    class Meta:
        model = Frequencia
        fields = {
            'aluno': ['exact'],
            'turma_disciplina': ['exact'],
            'presente': ['exact'],
            'data': ['exact'],
        }


class MensalidadeFilter(filters.FilterSet):
    """Filtro customizado para Mensalidades"""

    # Filtros por relacionamentos
    escola = filters.CharFilter(field_name='aluno__escola_id')
    turma = filters.CharFilter(field_name='aluno__turma_atual_id')

    # Filtros por datas
    vencimento_inicio = filters.DateFilter(field_name='data_vencimento', lookup_expr='gte')
    vencimento_fim = filters.DateFilter(field_name='data_vencimento', lookup_expr='lte')
    mes_competencia = filters.NumberFilter(field_name='competencia', lookup_expr='month')
    ano_competencia = filters.NumberFilter(field_name='competencia', lookup_expr='year')

    # Filtros por valores
    valor_min = filters.NumberFilter(field_name='valor_final', lookup_expr='gte')
    valor_max = filters.NumberFilter(field_name='valor_final', lookup_expr='lte')

    class Meta:
        model = Mensalidade
        fields = {
            'aluno': ['exact'],
            'responsavel_financeiro': ['exact'],
            'status': ['exact'],
            'competencia': ['exact', 'gte', 'lte'],
            'forma_pagamento': ['exact'],
        }