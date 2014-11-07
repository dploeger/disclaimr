# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrweb', '0002_auto_20141105_1241'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='resolve_sender',
            field=models.BooleanField(default=False, help_text='Resolve the sender by querying a directory server and provide data for the template tags inside a disclaimer', verbose_name='resolve the sender'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='resolve_sender_fail',
            field=models.BooleanField(default=False, help_text='Stop the action if the sender cannot be resolved.', verbose_name='fail when unable to resolve sender'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disclaimer',
            name='html_use_template',
            field=models.BooleanField(default=True, help_text='Use template tags in the html part. Available tags are: ${sender}, ${recipient} and all attributes, that are provided by resolving the sender in a directory server enclosed in ${}', verbose_name='use template tags'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disclaimer',
            name='html_use_text',
            field=models.BooleanField(default=True, help_text='Use the contents of the text part for the html part.', verbose_name='use text part'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disclaimer',
            name='template_fail',
            field=models.BooleanField(default=False, help_text="Don't use this disclaimer (and stop the associated action), if a template tag cannot be filled. If this is true, the template tag will be replaced with an empty string.", verbose_name="fail if template doesn't exist"),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disclaimer',
            name='text_use_template',
            field=models.BooleanField(default=True, help_text='Use template tags in the text part. Available tags are: %(sender)s, %(recipient)s and all attributes, that are provided by resolving the sender in a directory server', verbose_name='use template tags'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='directoryserverurl',
            name='url',
            field=models.CharField(help_text='URL of the directory server. For example: ldap://ldapserver:389/ or ldaps://ldapserver/', max_length=255, verbose_name='URL'),
            preserve_default=True,
        ),
    ]
