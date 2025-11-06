from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adiciona informações extras no token"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Adiciona claims customizados
        token['role'] = user.role
        token['nome'] = user.get_full_name()
        token['foto'] = user.foto

        # Adiciona escolas do usuário
        escolas = user.escolas.values_list('escola_id', flat=True)
        token['escolas'] = list(escolas)

        return token


class AlunoListSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source='usuario.get_full_name')
    foto = serializers.URLField(source='usuario.foto')
    responsaveis = serializers.SerializerMethodField()
    turno = serializers.CharField(source='turma_atual.turno')

    class Meta:
        model = Aluno
        fields = ['id', 'nome', 'matricula', 'foto', 'turma_atual',
                  'turno', 'status', 'responsaveis']

    def get_responsaveis(self, obj):
        return [{
            'nome': r.usuario.get_full_name(),
            'parentesco': r.parentesco,
            'telefone': r.usuario.telefone,
            'email': r.usuario.email
        } for r in obj.responsaveis.all()]


class ProfessorListSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source='usuario.get_full_name')
    disciplinas = serializers.SerializerMethodField()
    turmas = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = ['id', 'nome', 'email', 'formacao', 'disciplinas',
                  'turmas', 'carga_horaria', 'status']

    def get_disciplinas(self, obj):
        return list(obj.usuario.disciplinas_lecionadas.values_list(
            'disciplina__nome', flat=True
        ).distinct())