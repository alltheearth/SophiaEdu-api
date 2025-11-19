# apps/User/management/commands/corrigir_usuarios_sem_escola.py
# Crie esta estrutura de pastas: apps/User/management/commands/

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from apps.User.models import User
from apps.Schools.models import Escola, EscolaUsuario


class Command(BaseCommand):
    help = 'Verifica e corrige usuários sem escola vinculada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corrige os problemas encontrados',
        )
        parser.add_argument(
            '--escola-padrao',
            type=str,
            help='ID da escola padrão para vincular usuários órfãos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Verificando usuários sem escola...'))

        # Busca usuários sem escola (exceto SUPERUSER)
        usuarios_sem_escola = User.objects.exclude(role='SUPERUSER').annotate(
            num_escolas=Count('escolas', filter=Q(escolas__ativo=True))
        ).filter(num_escolas=0)

        total = usuarios_sem_escola.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ Todos os usuários estão vinculados a escolas!'))
            return

        self.stdout.write(self.style.ERROR(f'✗ Encontrados {total} usuários sem escola vinculada:'))

        for usuario in usuarios_sem_escola:
            self.stdout.write(f'  - {usuario.username} ({usuario.get_role_display()}) - ID: {usuario.id}')

        if not options['fix']:
            self.stdout.write(self.style.WARNING('\nUse --fix para corrigir automaticamente'))
            self.stdout.write(self.style.WARNING('Use --escola-padrao=<ID> para especificar a escola'))
            return

        # Correção automática
        escola_padrao_id = options.get('escola_padrao')

        if not escola_padrao_id:
            # Tenta pegar a primeira escola ativa
            primeira_escola = Escola.objects.filter(ativo=True).first()
            if not primeira_escola:
                self.stdout.write(self.style.ERROR('✗ Nenhuma escola ativa encontrada!'))
                return
            escola_padrao_id = str(primeira_escola.id)
            self.stdout.write(f'Usando escola padrão: {primeira_escola.nome}')

        try:
            escola_padrao = Escola.objects.get(id=escola_padrao_id, ativo=True)
        except Escola.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ Escola especificada não encontrada ou inativa!'))
            return

        # Vincula usuários à escola padrão
        corrigidos = 0
        for usuario in usuarios_sem_escola:
            EscolaUsuario.objects.create(
                escola=escola_padrao,
                usuario=usuario,
                role_na_escola=usuario.role
            )
            corrigidos += 1
            self.stdout.write(
                self.style.SUCCESS(f'✓ {usuario.username} vinculado a {escola_padrao.nome}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ {corrigidos} usuários corrigidos com sucesso!')
        )