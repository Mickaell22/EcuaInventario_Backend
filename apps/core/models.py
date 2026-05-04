import uuid
from django.db import models


class TenantManager(models.Manager):
    def for_tenant(self, negocio):
        return self.get_queryset().filter(negocio=negocio)


class TenantModel(models.Model):
    """
    Base abstracta para todos los modelos que pertenecen a un negocio.
    Garantiza que cada QuerySet se filtre por tenant antes de llegar al ViewSet.
    """
    negocio = models.ForeignKey(
        'negocios.Negocio',
        on_delete=models.CASCADE,
    )
    objects = TenantManager()

    class Meta:
        abstract = True
