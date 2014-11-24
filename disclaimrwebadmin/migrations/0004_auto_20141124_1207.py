# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0003_auto_20141124_1153'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rule',
            options={'ordering': ['position']},
        ),
        migrations.AddField(
            model_name='rule',
            name='position',
            field=models.PositiveIntegerField(default=0, help_text='Position of this rule in the rule processor.', verbose_name='number'),
            preserve_default=True,
        ),
    ]
