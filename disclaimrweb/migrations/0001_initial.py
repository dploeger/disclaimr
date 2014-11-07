# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('position', models.PositiveSmallIntegerField(verbose_name='Position')),
                ('name', models.CharField(help_text='The name of this action.', max_length=255, verbose_name='name')),
                ('description', models.TextField(help_text='The description of this action.', verbose_name='description', blank=True)),
                ('action', models.CharField(default=b'ADD', help_text='What action should be done?', max_length=30, verbose_name='action', choices=[(b'REPLACETAG', 'Replace a tag in the body with a disclaimer string'), (b'ADD', 'Add a disclaimer string to the body')])),
                ('only_mime', models.CharField(default=b'', help_text='Only carry out the action in the given mime type', max_length=255, verbose_name='mime type', blank=True)),
                ('action_parameters', models.TextField(default=b'', help_text='Parameters for the action (see the action documentation for details', verbose_name='action parameters', blank=True)),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'Action',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Disclaimer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text='Name of this disclaimer', max_length=255, verbose_name='name')),
                ('description', models.TextField(default=b'', help_text='A short description of this disclaimer', verbose_name='description', blank=True)),
                ('text', models.TextField(default=b'', help_text='A plain text disclaimer', verbose_name='text-part', blank=True)),
                ('html', models.TextField(default=b'', help_text='A html disclaimer (if not filled, the plain text disclaimer will be used.', verbose_name='html-part', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('position', models.PositiveSmallIntegerField(verbose_name='Position')),
                ('name', models.CharField(help_text='The name of this requirement.', max_length=255, verbose_name='name')),
                ('description', models.TextField(help_text='The description of this requirement.', verbose_name='description', blank=True)),
                ('sender_ip', models.IPAddressField(default=b'0.0.0.0/0', help_text='A filter for the IP-address of the sender server.', verbose_name='sender-IP address')),
                ('sender', models.TextField(default=b'^.*$', help_text='A regexp, that has to match the sender of a mail.', verbose_name='sender')),
                ('recipient', models.TextField(default=b'^.*$', help_text='A regexp, that has to match the recipient of a mail', verbose_name='recipient')),
                ('header', models.TextField(default=b'^.*$', help_text='A regexp, that has to match all headers of a mail', verbose_name='header-filter')),
                ('body', models.TextField(default=b'^.*$', help_text='A regexp, that has to match the body of a mail', verbose_name='body-filter')),
                ('action', models.CharField(default=b'ACCEPT', help_text='What to do, if this requirement is met?', max_length=30, verbose_name='action', choices=[(b'ACCEPT', 'Accept rule'), (b'DENY', 'Deny rule')])),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'Requirement',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of this rule.', max_length=255, verbose_name='name')),
                ('description', models.TextField(help_text='The description of this rule.', verbose_name='description', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='requirement',
            name='rule',
            field=models.ForeignKey(to='disclaimrweb.Rule'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='disclaimer',
            field=models.ForeignKey(to='disclaimrweb.Disclaimer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='rule',
            field=models.ForeignKey(to='disclaimrweb.Rule'),
            preserve_default=True,
        ),
    ]
