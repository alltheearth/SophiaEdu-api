"""
Configurações de desenvolvimento
"""
from .base import *
from decouple import Config, RepositoryEnv

# Carrega .env da raiz do projeto
env_path = os.path.join(BASE_DIR, '.env')
if not os.path.exists(env_path):
    raise FileNotFoundError(f"Arquivo .env não encontrado em {env_path}")

config = Config(RepositoryEnv(env_path))

# =========================
# SEGURANÇA
# =========================
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

DEBUG = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0').split(',')

# =========================
# DATABASE
# =========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='postgres'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# =========================
# CORS (Mais permissivo em desenvolvimento)
# =========================
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# Opcional: permitir todas as origens em desenvolvimento (NÃO USE EM PRODUÇÃO)
# CORS_ALLOW_ALL_ORIGINS = True

# =========================
# LOGGING (Verboso para debug)
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Mostra queries SQL
            'propagate': False,
        },
    },
}

# =========================
# ASAAS INTEGRATION
# =========================
ASAAS_API_URL = config('ASAAS_API_URL', default='https://sandbox.asaas.com/api/v3')
ASAAS_ENVIRONMENT = 'sandbox'

# =========================
# SUPABASE STORAGE
# =========================
SUPABASE_URL = config('SUPABASE_URL', default='')
SUPABASE_KEY = config('SUPABASE_KEY', default='')
SUPABASE_STORAGE_BUCKET = config('SUPABASE_STORAGE_BUCKET', default='uploads')

# =========================
# SEGURANÇA (Relaxada para desenvolvimento)
# =========================
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173'
).split(',')

# Desabilitar HTTPS redirect em desenvolvimento
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# =========================
# SIMPLE JWT (Configurações específicas de dev)
# =========================
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY