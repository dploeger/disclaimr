# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0009_rule_continue_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='disclaimer',
            name='use_html_fallback',
            field=models.BooleanField(default=False, help_text="Usually, disclaimr tries to identify the content type of the sent mail and uses the matching disclaimer. If that doesn't work, use HTML instead of text.", verbose_name='use HTML as a fallback'),
            preserve_default=True,
        ),
    ]
