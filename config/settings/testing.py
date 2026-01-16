"""
Configurações para testes
"""
from .base import *

# =========================
# SEGURANÇA
# =========================
SECRET_KEY = 'django-insecure-test-key-not-for-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

# =========================
# DATABASE (Usar banco em memória para testes rápidos)
# =========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Se preferir usar PostgreSQL para testes (mais realista):
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'test_db',
#         'USER': 'postgres',
#         'PASSWORD': 'postgres',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# =========================
# PASSWORD HASHERS (Mais rápido para testes)
# =========================
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# =========================
# CORS
# =========================
CORS_ALLOW_ALL_ORIGINS = True

# =========================
# LOGGING (Mínimo)
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# =========================
# EMAIL (Mock para testes)
# =========================
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# =========================
# CACHE (Usar dummy cache)
# =========================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# =========================
# CELERY (Executar tasks de forma síncrona nos testes)
# =========================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True