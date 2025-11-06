"""
Comando Django para aguardar o banco de dados estar pronto
Salve em: sophia/management/commands/wait_for_db.py
"""
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Aguarda o banco de dados estar disponível"""
    help = 'Aguarda o banco de dados estar disponível'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Aguardando banco de dados...')
        db_conn = None
        max_retries = 30
        retry_count = 0

        while not db_conn and retry_count < max_retries:
            try:
                db_conn = connections['default']
                db_conn.cursor()
                self.stdout.write(self.style.SUCCESS('✅ Banco de dados disponível!'))
            except OperationalError:
                retry_count += 1
                self.stdout.write(
                    f'⏳ Banco de dados indisponível, aguardando... '
                    f'({retry_count}/{max_retries})'
                )
                time.sleep(1)

        if retry_count >= max_retries:
            self.stdout.write(
                self.style.ERROR('❌ Não foi possível conectar ao banco de dados!')
            )
            exit(1)