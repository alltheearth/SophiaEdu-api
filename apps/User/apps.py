
# ============================================
# apps/User/apps.py
# ============================================
from django.apps import AppConfig

class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.User'
    label = 'User'
    verbose_name = 'Usuários'

    def ready(self):
        """Importa os signals quando o app estiver pronto"""
        try:
            import apps.User.signals
        except ImportError:
            pass
