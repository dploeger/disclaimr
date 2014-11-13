# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='requirement',
            options={'verbose_name': 'Requirement'},
        ),
        migrations.RemoveField(
            model_name='requirement',
            name='position',
        ),
        migrations.AlterField(
            model_name='requirement',
            name='header',
            field=models.TextField(default=b'^.*$', help_text='A regexp, that has to match all headers of a mail. The headers will be represented in a key: value - format.', verbose_name='header-filter'),
            preserve_default=True,
        ),
    ]
