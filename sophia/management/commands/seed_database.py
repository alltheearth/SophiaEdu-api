# sophia/management/commands/seed_database.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from sophia.models import (
    User, Escola, EscolaUsuario, Professor, Aluno, Responsavel,
    AlunoResponsavel, AnoLetivo, Turma, Disciplina, TurmaDisciplina,
    PeriodoAvaliativo, Nota, Frequencia, Mensalidade
)


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de teste'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Iniciando seed do banco de dados...')

        # Limpar dados existentes (CUIDADO EM PRODUÇÃO!)
        self.stdout.write('🗑️  Limpando dados antigos...')
        
        # ========== CRIAR ESCOLA ==========
        self.stdout.write('🏫 Criando escola...')
        escola, created = Escola.objects.get_or_create(
            cnpj='12.345.678/0001-90',
            defaults={
                'nome': 'Colégio Luz do Saber',
                'endereco': 'Rua Principal, 123 - Centro',
                'telefone': '(11) 98765-4321',
                'email': 'contato@colegioluzdosaber.com.br',
                'ativo': True,
                'plano': 'PREMIUM'
            }
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Escola criada: {escola.nome}'))

        # ========== CRIAR GESTOR ==========
        self.stdout.write('👤 Criando usuários...')
        
        gestor_user, created = User.objects.get_or_create(
            username='gestor',
            defaults={
                'email': 'gestor@escola.com',
                'first_name': 'Maria',
                'last_name': 'Silva',
                'role': 'GESTOR',
                'cpf': '123.456.789-00',
                'telefone': '(11) 91234-5678',
                'ativo': True,
                'email_verificado': True,
                'primeiro_acesso': False
            }
        )
        if created:
            gestor_user.set_password('senha123')
            gestor_user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Gestor criado: {gestor_user.username}'))

        # Vincular gestor à escola
        EscolaUsuario.objects.get_or_create(
            escola=escola,
            usuario=gestor_user,
            defaults={'role_na_escola': 'GESTOR', 'ativo': True}
        )

        # ========== CRIAR COORDENADOR ==========
        coordenador_user, created = User.objects.get_or_create(
            username='coordenador',
            defaults={
                'email': 'coordenador@escola.com',
                'first_name': 'João',
                'last_name': 'Santos',
                'role': 'COORDENADOR',
                'cpf': '234.567.890-00',
                'telefone': '(11) 91234-5679',
                'ativo': True,
                'email_verificado': True,
                'primeiro_acesso': False
            }
        )
        if created:
            coordenador_user.set_password('senha123')
            coordenador_user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Coordenador criado: {coordenador_user.username}'))

        EscolaUsuario.objects.get_or_create(
            escola=escola,
            usuario=coordenador_user,
            defaults={'role_na_escola': 'COORDENADOR', 'ativo': True}
        )

        # ========== CRIAR PROFESSORES ==========
        professores_data = [
            {'username': 'prof.joao', 'first_name': 'João', 'last_name': 'Oliveira', 'cpf': '345.678.901-00', 'formacao': 'Matemática', 'disciplina': 'Matemática'},
            {'username': 'prof.ana', 'first_name': 'Ana', 'last_name': 'Costa', 'cpf': '456.789.012-00', 'formacao': 'Letras', 'disciplina': 'Português'},
            {'username': 'prof.carlos', 'first_name': 'Carlos', 'last_name': 'Lima', 'cpf': '567.890.123-00', 'formacao': 'História', 'disciplina': 'História'},
            {'username': 'prof.lucia', 'first_name': 'Lúcia', 'last_name': 'Fernandes', 'cpf': '678.901.234-00', 'formacao': 'Biologia', 'disciplina': 'Ciências'},
        ]

        professores = []
        for prof_data in professores_data:
            user, created = User.objects.get_or_create(
                username=prof_data['username'],
                defaults={
                    'email': f"{prof_data['username']}@escola.com",
                    'first_name': prof_data['first_name'],
                    'last_name': prof_data['last_name'],
                    'role': 'PROFESSOR',
                    'cpf': prof_data['cpf'],
                    'telefone': '(11) 91234-5680',
                    'ativo': True,
                    'email_verificado': True,
                    'primeiro_acesso': False
                }
            )
            if created:
                user.set_password('senha123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Professor criado: {user.username}'))

            # Criar perfil de professor
            professor, _ = Professor.objects.get_or_create(
                usuario=user,
                defaults={
                    'escola': escola,
                    'formacao': prof_data['formacao'],
                    'especializacao': f'Especialização em {prof_data["formacao"]}',
                    'data_admissao': date(2023, 1, 1),
                    'carga_horaria': 40,
                    'turno': 'MATUTINO',
                    'salario': Decimal('5000.00'),
                    'status': 'ATIVO'
                }
            )
            professores.append(professor)

            # Vincular à escola
            EscolaUsuario.objects.get_or_create(
                escola=escola,
                usuario=user,
                defaults={'role_na_escola': 'PROFESSOR', 'ativo': True}
            )

        # ========== CRIAR ANO LETIVO ==========
        self.stdout.write('📅 Criando ano letivo...')
        ano_letivo, created = AnoLetivo.objects.get_or_create(
            escola=escola,
            ano=2025,
            defaults={
                'data_inicio': date(2025, 2, 1),
                'data_fim': date(2025, 12, 20),
                'ativo': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Ano letivo criado: {ano_letivo.ano}'))

        # ========== CRIAR PERÍODOS AVALIATIVOS ==========
        periodos_data = [
            {'nome': '1º Bimestre', 'data_inicio': date(2025, 2, 1), 'data_fim': date(2025, 4, 30), 'ordem': 1},
            {'nome': '2º Bimestre', 'data_inicio': date(2025, 5, 1), 'data_fim': date(2025, 7, 31), 'ordem': 2},
            {'nome': '3º Bimestre', 'data_inicio': date(2025, 8, 1), 'data_fim': date(2025, 10, 31), 'ordem': 3},
            {'nome': '4º Bimestre', 'data_inicio': date(2025, 11, 1), 'data_fim': date(2025, 12, 20), 'ordem': 4},
        ]

        periodos = []
        for periodo_data in periodos_data:
            periodo, _ = PeriodoAvaliativo.objects.get_or_create(
                ano_letivo=ano_letivo,
                ordem=periodo_data['ordem'],
                defaults=periodo_data
            )
            periodos.append(periodo)

        # ========== CRIAR DISCIPLINAS ==========
        self.stdout.write('📚 Criando disciplinas...')
        disciplinas_data = [
            {'nome': 'Matemática', 'codigo': 'MAT', 'carga_horaria': 5},
            {'nome': 'Português', 'codigo': 'PORT', 'carga_horaria': 5},
            {'nome': 'História', 'codigo': 'HIST', 'carga_horaria': 3},
            {'nome': 'Ciências', 'codigo': 'CIEN', 'carga_horaria': 3},
            {'nome': 'Geografia', 'codigo': 'GEO', 'carga_horaria': 3},
            {'nome': 'Inglês', 'codigo': 'ING', 'carga_horaria': 2},
        ]

        disciplinas = []
        for disc_data in disciplinas_data:
            disciplina, created = Disciplina.objects.get_or_create(
                escola=escola,
                codigo=disc_data['codigo'],
                defaults=disc_data
            )
            disciplinas.append(disciplina)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Disciplina criada: {disciplina.nome}'))

        # ========== CRIAR TURMAS ==========
        self.stdout.write('🏫 Criando turmas...')
        turmas_data = [
            {'nome': '5º Ano A', 'serie': '5º Ano', 'turno': 'MATUTINO', 'sala': '201'},
            {'nome': '5º Ano B', 'serie': '5º Ano', 'turno': 'VESPERTINO', 'sala': '202'},
            {'nome': '6º Ano A', 'serie': '6º Ano', 'turno': 'MATUTINO', 'sala': '203'},
        ]

        turmas = []
        for turma_data in turmas_data:
            turma, created = Turma.objects.get_or_create(
                escola=escola,
                ano_letivo=ano_letivo,
                nome=turma_data['nome'],
                defaults={
                    **turma_data,
                    'capacidade_maxima': 30,
                    'coordenador': coordenador_user,
                    'professor_titular': professores[0].usuario
                }
            )
            turmas.append(turma)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Turma criada: {turma.nome}'))

                # Vincular disciplinas à turma
                for i, disciplina in enumerate(disciplinas[:4]):  # Primeiras 4 disciplinas
                    professor = professores[i % len(professores)]
                    TurmaDisciplina.objects.get_or_create(
                        turma=turma,
                        disciplina=disciplina,
                        defaults={'professor': professor.usuario}
                    )

        # ========== CRIAR ALUNOS E RESPONSÁVEIS ==========
        self.stdout.write('👨‍👩‍👧‍👦 Criando alunos e responsáveis...')
        
        alunos_data = [
            {
                'aluno': {'first_name': 'Pedro', 'last_name': 'Almeida', 'matricula': '2025001'},
                'responsavel': {'first_name': 'Carlos', 'last_name': 'Almeida', 'cpf': '111.222.333-44', 'parentesco': 'Pai'}
            },
            {
                'aluno': {'first_name': 'Julia', 'last_name': 'Santos', 'matricula': '2025002'},
                'responsavel': {'first_name': 'Mariana', 'last_name': 'Santos', 'cpf': '222.333.444-55', 'parentesco': 'Mãe'}
            },
            {
                'aluno': {'first_name': 'Lucas', 'last_name': 'Silva', 'matricula': '2025003'},
                'responsavel': {'first_name': 'Roberto', 'last_name': 'Silva', 'cpf': '333.444.555-66', 'parentesco': 'Pai'}
            },
        ]

        for idx, aluno_data in enumerate(alunos_data):
            # Criar usuário aluno
            aluno_user, created = User.objects.get_or_create(
                username=f"aluno{idx+1}",
                defaults={
                    'email': f"aluno{idx+1}@escola.com",
                    'first_name': aluno_data['aluno']['first_name'],
                    'last_name': aluno_data['aluno']['last_name'],
                    'role': 'ALUNO',
                    'cpf': f'888.{idx+1:03d}.{idx+1:03d}-{idx+1:02d}',
                    'telefone': f'(11) 99999-{idx+1:04d}',
                    'ativo': True,
                    'email_verificado': True,
                    'primeiro_acesso': False
                }
            )
            if created:
                aluno_user.set_password('senha123')
                aluno_user.save()

            # Criar perfil aluno
            turma = turmas[idx % len(turmas)]  # Distribui alunos entre turmas
            aluno, _ = Aluno.objects.get_or_create(
                usuario=aluno_user,
                defaults={
                    'escola': escola,
                    'matricula': aluno_data['aluno']['matricula'],
                    'data_nascimento': date(2013, 1, 1 + idx),
                    'turma_atual': turma,
                    'status': 'ATIVO'
                }
            )

            EscolaUsuario.objects.get_or_create(
                escola=escola,
                usuario=aluno_user,
                defaults={'role_na_escola': 'ALUNO', 'ativo': True}
            )

            # Criar responsável
            resp_user, created = User.objects.get_or_create(
                username=f"responsavel{idx+1}",
                defaults={
                    'email': f"responsavel{idx+1}@email.com",
                    'first_name': aluno_data['responsavel']['first_name'],
                    'last_name': aluno_data['responsavel']['last_name'],
                    'role': 'RESPONSAVEL',
                    'cpf': aluno_data['responsavel']['cpf'],
                    'telefone': f'(11) 98888-{idx+1:04d}',
                    'ativo': True,
                    'email_verificado': True,
                    'primeiro_acesso': False
                }
            )
            if created:
                resp_user.set_password('senha123')
                resp_user.save()

            responsavel, _ = Responsavel.objects.get_or_create(
                usuario=resp_user,
                defaults={
                    'cpf': aluno_data['responsavel']['cpf'],
                    'parentesco': aluno_data['responsavel']['parentesco'],
                    'profissao': 'Engenheiro',
                    'endereco': 'Rua Exemplo, 100'
                }
            )

            EscolaUsuario.objects.get_or_create(
                escola=escola,
                usuario=resp_user,
                defaults={'role_na_escola': 'RESPONSAVEL', 'ativo': True}
            )

            # Vincular aluno ao responsável
            AlunoResponsavel.objects.get_or_create(
                aluno=aluno,
                responsavel=responsavel,
                defaults={
                    'responsavel_financeiro': True,
                    'prioridade': 1
                }
            )

            self.stdout.write(self.style.SUCCESS(f'✅ Aluno e responsável criados: {aluno_user.first_name}'))

        self.stdout.write(self.style.SUCCESS('\n✅ SEED COMPLETO!'))
        self.stdout.write('\n📋 CREDENCIAIS DE ACESSO:')
        self.stdout.write('   Gestor: gestor / senha123')
        self.stdout.write('   Coordenador: coordenador / senha123')
        self.stdout.write('   Professor: prof.joao / senha123')
        self.stdout.write('   Responsável: responsavel1 / senha123')
        self.stdout.write('   Aluno: aluno1 / senha123\n')