# serializers.py

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