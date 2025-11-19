from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import User


@receiver(pre_save, sender=User)
def validar_usuario_antes_salvar(sender, instance, **kwargs):
    """
    Valida se usuário não-SUPERUSER tem escola vinculada
    antes de salvar (exceto na criação inicial)
    """
    # Ignora validação na criação (pk ainda não existe)
    if not instance.pk:
        return

    # Ignora se for SUPERUSER
    if instance.role == 'SUPERUSER':
        return

    # Verifica se tem pelo menos uma escola ativa vinculada
    if not instance.escolas.filter(ativo=True).exists():
        raise ValidationError(
            f"Usuário com role '{instance.get_role_display()}' precisa estar "
            "vinculado a pelo menos uma escola ativa."
        )


@receiver(post_save, sender=User)
def verificar_escola_apos_criar(sender, instance, created, **kwargs):
    """
    Após criar usuário, verifica se ele precisa de escola vinculada
    """
    if created and instance.role != 'SUPERUSER':
        # Apenas loga warning, pois a validação real é feita no serializer
        if not instance.escolas.exists():
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Usuário {instance.username} ({instance.role}) criado "
                "sem vínculo com escola. Isso pode causar problemas."
            )