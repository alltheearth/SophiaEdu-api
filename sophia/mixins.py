# sophia/mixins.py (CRIAR)
class EscolaFilterMixin:
    """Mixin para filtrar automaticamente por escola"""

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.role == 'SUPERUSER':
            return queryset

        # Obter escola_id do header ou query param
        escola_id = (
                self.request.headers.get('X-Escola-ID') or
                self.request.query_params.get('escola_id')
        )

        if not escola_id:
            # Se não informado, usar escolas do usuário
            escolas = user.escolas.values_list('escola_id', flat=True)
            return queryset.filter(escola_id__in=escolas)

        # Validar se usuário tem acesso à escola
        if not user.escolas.filter(escola_id=escola_id).exists():
            return queryset.none()

        return queryset.filter(escola_id=escola_id)