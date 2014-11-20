# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrwebadmin', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='disclaimer',
            name='html_charset',
            field=models.CharField(default=b'utf-8', help_text='Charset of the html field', max_length=255, verbose_name='Charset'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disclaimer',
            name='text_charset',
            field=models.CharField(default=b'utf-8', help_text='Charset of the text field', max_length=255, verbose_name='Charset'),
            preserve_default=True,
        ),
    ]
