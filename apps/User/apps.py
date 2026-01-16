from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.User'
    verbose_name = 'Usuários'

    def ready(self):
        """Importa os signals quando o app estiver pronto"""
        import apps.User.signals  # CORRIGIDO: caminho minúsculo