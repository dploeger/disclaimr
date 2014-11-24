# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0002_auto_20141120_1456'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='action',
            field=models.SmallIntegerField(default=1, help_text='What action should be done?', verbose_name='action', choices=[(0, 'Replace a tag in the body with a disclaimer string'), (1, 'Add a disclaimer string to the body'), (2, 'Add the disclaimer using an additional MIME part')]),
            preserve_default=True,
        ),
    ]
