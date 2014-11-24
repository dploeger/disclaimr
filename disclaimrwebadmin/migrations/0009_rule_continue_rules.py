# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0008_auto_20141124_1236'),
    ]

    operations = [
        migrations.AddField(
            model_name='rule',
            name='continue_rules',
            field=models.BooleanField(default=False, help_text='Continue with other possibly matching rules after this one is processed?', verbose_name='Continue after this rule'),
            preserve_default=True,
        ),
    ]
