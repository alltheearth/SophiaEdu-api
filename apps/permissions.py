# permissions.py

from rest_framework import permissions


class IsSuperUser(permissions.BasePermission):
    """Apenas SuperUser"""

    def has_permission(self, request, view):
        return request.user.role == 'SUPERUSER'


class IsGestorOrAbove(permissions.BasePermission):
    """Gestor ou SuperUser"""

    def has_permission(self, request, view):
        return request.user.role in ['SUPERUSER', 'GESTOR']


class IsCoordenadorOrAbove(permissions.BasePermission):
    """Coordenador, Gestor ou SuperUser"""

    def has_permission(self, request, view):
        return request.user.role in ['SUPERUSER', 'GESTOR', 'COORDENADOR']


class IsProfessorOrAbove(permissions.BasePermission):
    """Professor ou acima"""

    def has_permission(self, request, view):
        return request.user.role in ['SUPERUSER', 'GESTOR', 'COORDENADOR', 'PROFESSOR']


class CanAccessEscola(permissions.BasePermission):
    """Verifica se usuário tem acesso à escola"""

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'SUPERUSER':
            return True

        # Verifica se usuário pertence à escola do objeto
        if hasattr(obj, 'escola'):
            return obj.escola in request.user.escolas.all()

        return False


class CanEditNota(permissions.BasePermission):
    """Professor só pode editar notas das suas turmas"""

    def has_object_permission(self, request, view, obj):
        if request.user.role in ['SUPERUSER', 'GESTOR']:
            return True

        if request.user.role == 'COORDENADOR':
            return request.method in permissions.SAFE_METHODS  # Só leitura

        if request.user.role == 'PROFESSOR':
            # Verifica se é professor da disciplina
            return obj.turma_disciplina.professor == request.user

        return False


class CanAccessAlunoData(permissions.BasePermission):
    """Responsável só acessa dados dos próprios filhos"""

    def has_object_permission(self, request, view, obj):
        if request.user.role in ['SUPERUSER', 'GESTOR', 'COORDENADOR', 'PROFESSOR']:
            return True

        if request.user.role == 'RESPONSAVEL':
            # Verifica se o aluno é filho do responsável
            responsavel = request.user.responsavel_profile
            return obj.aluno in responsavel.alunos.all()

        return False