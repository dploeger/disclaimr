# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0007_auto_20141124_1229'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rule',
            options={'ordering': ['position']},
        ),
        migrations.AlterField(
            model_name='rule',
            name='position',
            field=models.PositiveIntegerField(default=0, help_text='The position inside the rule processor', verbose_name='position'),
            preserve_default=True,
        ),
    ]
