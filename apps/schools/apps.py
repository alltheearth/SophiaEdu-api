from django.apps import AppConfig


class SchoolsConfig(AppConfig):  # CORRIGIDO: nome da classe
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.Schools'