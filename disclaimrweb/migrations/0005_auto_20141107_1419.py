# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrweb', '0004_auto_20141107_1411'),
    ]

    operations = [
        migrations.AddField(
            model_name='requirement',
            name='sender_ip_cidr',
            field=models.CharField(default=b'0', help_text='The CIDR-netmask for the sender ip address', max_length=2, verbose_name='netmask'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='requirement',
            name='sender_ip',
            field=models.GenericIPAddressField(default=b'0.0.0.0', help_text='A filter for the IP-address of the sender server.', verbose_name='sender-IP address'),
            preserve_default=True,
        ),
    ]
