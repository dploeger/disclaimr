# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0005_auto_20141124_1225'),
    ]

    operations = [
        migrations.AddField(
            model_name='rule',
            name='position',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
    ]
