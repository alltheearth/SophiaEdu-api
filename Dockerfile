# Etapa 1: Base
FROM python:3.11-slim as base

# Variáveis de ambiente para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Etapa 2: Dependências
FROM base as dependencies

# Instala Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Configura Poetry para não criar virtualenv
RUN poetry config virtualenvs.create false

# Copia arquivos de dependências
COPY pyproject.toml poetry.lock* README.md /app/

# Instala dependências
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Etapa 3: Aplicação
FROM base as application

# Copia dependências instaladas da etapa anterior
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copia o código da aplicação
COPY . /app/

# Cria diretórios necessários
RUN mkdir -p /app/staticfiles /app/media

# Coleta arquivos estáticos
RUN python manage.py collectstatic --noinput || true

# Expõe a porta
EXPOSE 8000

# Copia o código da aplicação
COPY . /app/

# Copia o script de inicialização
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]