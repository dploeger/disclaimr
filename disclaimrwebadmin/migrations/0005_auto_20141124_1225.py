# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0004_auto_20141124_1207'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rule',
            options={'ordering': ['name']},
        ),
        migrations.RemoveField(
            model_name='rule',
            name='position',
        ),
    ]
