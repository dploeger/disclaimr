# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disclaimrweb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectoryServer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of this action.', max_length=255, verbose_name='name')),
                ('description', models.TextField(help_text='The description of this action.', verbose_name='description', blank=True)),
                ('enabled', models.BooleanField(default=True, help_text='Is this directory server enabled?', verbose_name='enabled')),
                ('base_dn', models.CharField(help_text='The LDAP base dn.', max_length=255, verbose_name='base-dn')),
                ('auth', models.SmallIntegerField(default=0, help_text='Authentication method to connect to the server', verbose_name='auth_method', choices=[(0, 'None'), (1, 'Simple')])),
                ('userdn', models.CharField(default=b'', help_text='DN of the user to authenticate with', max_length=255, verbose_name='user-DN', blank=True)),
                ('password', models.CharField(default=b'', help_text='Password to authenticate with', max_length=255, verbose_name='password', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DirectoryServerURL',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(help_text='URL of the directory server. For example: ldap://ldapserver:389/ or ldaps://ldapserver/', verbose_name='URL')),
                ('position', models.PositiveSmallIntegerField(verbose_name='Position')),
                ('directory_server', models.ForeignKey(to='disclaimrweb.DirectoryServer')),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'URL',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='action',
            name='enabled',
            field=models.BooleanField(default=True, help_text='Is this action enabled?', verbose_name='enabled'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='requirement',
            name='enabled',
            field=models.BooleanField(default=True, help_text='Is this requirement enabled?', verbose_name='enabled'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='action',
            name='action',
            field=models.SmallIntegerField(default=1, help_text='What action should be done?', verbose_name='action', choices=[(0, 'Replace a tag in the body with a disclaimer string'), (1, 'Add a disclaimer string to the body')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='requirement',
            name='action',
            field=models.SmallIntegerField(default=0, help_text='What to do, if this requirement is met?', verbose_name='action', choices=[(0, 'Accept rule'), (1, 'Deny rule')]),
            preserve_default=True,
        ),
    ]
