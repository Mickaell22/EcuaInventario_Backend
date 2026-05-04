import uuid
from django.db import models


class Negocio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, blank=True)
    seed_color = models.CharField(max_length=7, default='#1976D2')
    theme_mode = models.CharField(
        max_length=10,
        choices=[('light', 'Claro'), ('dark', 'Oscuro'), ('system', 'Sistema')],
        default='system',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'negocio'
        verbose_name_plural = 'negocios'

    def __str__(self):
        return self.nombre
