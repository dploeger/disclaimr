# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrweb', '0005_auto_20141107_1419'),
    ]

    operations = [
        migrations.AddField(
            model_name='directoryserver',
            name='search_query',
            field=models.TextField(default=b'mail=${email}', help_text='A search query to run against the directory server to fetch the ldap object when resolving. ${email} will be replaced when resolving.', verbose_name='search query'),
            preserve_default=True,
        ),
    ]
