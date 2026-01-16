"""
Configurações de produção
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
SECRET_KEY = config('SECRET_KEY')  # OBRIGATÓRIO em produção

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')

# =========================
# DATABASE
# =========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# =========================
# CORS (Restritivo em produção)
# =========================
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS').split(',')
CORS_ALLOW_CREDENTIALS = True

# =========================
# SEGURANÇA (Produção)
# =========================
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS').split(',')

# =========================
# LOGGING (Menos verboso)
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Criar pasta de logs se não existir
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# =========================
# ASAAS INTEGRATION
# =========================
ASAAS_API_URL = config('ASAAS_API_URL', default='https://api.asaas.com/v3')
ASAAS_ENVIRONMENT = 'production'

# =========================
# SUPABASE STORAGE
# =========================
SUPABASE_URL = config('SUPABASE_URL')
SUPABASE_KEY = config('SUPABASE_KEY')
SUPABASE_STORAGE_BUCKET = config('SUPABASE_STORAGE_BUCKET', default='uploads')

# =========================
# SIMPLE JWT
# =========================
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

# =========================
# ARQUIVOS ESTÁTICOS (AWS S3 ou similar)
# =========================
# Descomente e configure se usar S3
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
# AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')