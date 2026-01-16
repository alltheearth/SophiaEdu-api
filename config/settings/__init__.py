"""
Seletor de configurações baseado na variável de ambiente DJANGO_SETTINGS_MODULE
ou na variável DJANGO_ENV
"""
import os
from decouple import config

# Determina qual ambiente usar
ENVIRONMENT = config('DJANGO_ENV', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'testing':
    from .testing import *
else:
    from .development import *

print(f"🚀 Django rodando em modo: {ENVIRONMENT.upper()}")