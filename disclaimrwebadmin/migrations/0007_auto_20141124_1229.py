# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0006_rule_position'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rule',
            options={'ordering': ('position',)},
        ),
    ]
