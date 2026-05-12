from django.db import migrations, models


def set_default_motivos(apps, schema_editor):
    Movimiento = apps.get_model('inventario', 'Movimiento')
    Movimiento.objects.filter(tipo='entrada', motivo='').update(motivo='compra')
    Movimiento.objects.filter(tipo='salida', motivo='').update(motivo='consumo')


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='movimiento',
            name='motivo',
            field=models.CharField(
                blank=True,
                default='',
                max_length=10,
                choices=[
                    ('compra', 'Compra'),
                    ('ajuste', 'Ajuste de inventario'),
                    ('consumo', 'Consumo'),
                    ('merma', 'Merma / pérdida'),
                ],
            ),
        ),
        migrations.RunPython(set_default_motivos, migrations.RunPython.noop),
    ]
