# 🐳 Guia de Uso do Docker - EleveIA API

## 📋 Pré-requisitos

- Docker instalado
- Docker Compose instalado
- Arquivo `.env` configurado

## 🚀 Como Usar

### 1️⃣ Configuração Inicial

Copie o arquivo de exemplo e configure suas variáveis:

```bash
cp .env.example .env
```

Edite o `.env` conforme sua necessidade (PostgreSQL local ou Supabase).

### 2️⃣ Criar a Estrutura de Diretórios

Crie a estrutura de comandos management:

```bash
mkdir -p sophia/management/commands
touch sophia/management/__init__.py
touch sophia/management/commands/__init__.py
```

Depois copie o conteúdo de `wait_for_db.py` para:
```bash
sophia/management/commands/wait_for_db.py
```

## 🎯 Cenários de Uso

### 🏠 Cenário 1: PostgreSQL Local (Docker)

**Configuração no `.env`:**
```bash
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

**Iniciar os serviços:**
```bash
# Build e start
docker-compose up --build

# Ou em background
docker-compose up -d --build
```

**Criar superusuário:**
```bash
docker-compose exec web python manage.py createsuperuser
```

### ☁️ Cenário 2: Supabase (Banco Externo)

**Configuração no `.env`:**
```bash
DB_NAME=postgres
DB_USER=postgres.nclbzvjypyjayiywwxgz
DB_PASSWORD=5ri*jPJuK@4jXK!
DB_HOST=aws-1-us-east-1.pooler.supabase.com
DB_PORT=6543
```

**Desabilitar PostgreSQL local:**
```bash
# Edite docker-compose.yml e adicione profile ao serviço db:
# profiles: ["local-db"]
```

**Iniciar apenas a aplicação:**
```bash
docker-compose up web --build
```

### 🚀 Cenário 3: Produção com Nginx

**Iniciar com Nginx:**
```bash
docker-compose --profile production up -d --build
```

Isso irá:
- Iniciar o PostgreSQL (se configurado)
- Iniciar a aplicação Django
- Iniciar o Nginx na porta 80

## 🔧 Comandos Úteis

### Ver logs
```bash
# Todos os serviços
docker-compose logs -f

# Apenas a aplicação
docker-compose logs -f web

# Apenas o banco
docker-compose logs -f db
```

### Executar comandos Django
```bash
# Migrations
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Shell
docker-compose exec web python manage.py shell

# Criar superuser
docker-compose exec web python manage.py createsuperuser

# Coletar static files
docker-compose exec web python manage.py collectstatic
```

### Parar e remover containers
```bash
# Parar
docker-compose stop

# Parar e remover
docker-compose down

# Parar, remover e limpar volumes (⚠️ apaga dados do banco)
docker-compose down -v
```

### Rebuild completo
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Acessar bash do container
```bash
docker-compose exec web bash
```

## 🌐 Acessar a Aplicação

- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/
- **Nginx (produção)**: http://localhost/

## 🔍 Troubleshooting

### Erro de conexão com banco de dados

1. Verifique se o serviço db está rodando:
```bash
docker-compose ps
```

2. Teste a conexão:
```bash
docker-compose exec db psql -U postgres -d postgres
```

3. Verifique as variáveis de ambiente:
```bash
docker-compose exec web env | grep DB_
```

### Permissões de arquivo

Se tiver problemas com permissões:
```bash
sudo chown -R $USER:$USER .
```

### Limpar tudo e começar do zero

```bash
docker-compose down -v
docker system prune -a
docker volume prune
```

## 📝 Estrutura de Arquivos

```
eleveia-api/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env
├── .env.example
├── nginx.conf (opcional)
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── eleveai/
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── wait_for_db.py
│   ├── models.py
│   ├── views.py
│   └── ...
└── staticfiles/
```

## 🔒 Segurança em Produção

Para produção, lembre-se de:

1. **Mudar DEBUG para False:**
```bash
DEBUG=False
```

2. **Usar SECRET_KEY forte:**
```bash
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
```

3. **Configurar ALLOWED_HOSTS:**
```bash
ALLOWED_HOSTS=seudominio.com,www.seudominio.com
```

4. **Usar HTTPS (SSL/TLS)**

5. **Não commitar o .env no git**

## 💡 Dicas

- Use `docker-compose up` sem `-d` para ver logs em tempo real durante desenvolvimento
- Configure volumes para persistir dados importantes
- Use `--build` quando mudar dependências no `requirements.txt` ou `pyproject.toml`
- Para desenvolvimento, os volumes mapeiam seu código local, permitindo hot-reload

## 📚 Recursos Adicionais

- [Documentação Docker](https://docs.docker.com/)
- [Documentação Docker Compose](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)