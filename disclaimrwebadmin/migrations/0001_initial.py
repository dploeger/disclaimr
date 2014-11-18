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
                ('enabled', models.BooleanField(default=True, help_text='Is this action enabled?', verbose_name='enabled')),
                ('description', models.TextField(help_text='The description of this action.', verbose_name='description', blank=True)),
                ('action', models.SmallIntegerField(default=1, help_text='What action should be done?', verbose_name='action', choices=[(0, 'Replace a tag in the body with a disclaimer string'), (1, 'Add a disclaimer string to the body')])),
                ('only_mime', models.CharField(default=b'', help_text='Only carry out the action in the given mime type', max_length=255, verbose_name='mime type', blank=True)),
                ('action_parameters', models.TextField(default=b'', help_text='Parameters for the action (see the action documentation for details)', verbose_name='action parameters', blank=True)),
                ('resolve_sender', models.BooleanField(default=False, help_text='Resolve the sender by querying a directory server and provide data for the template tags inside a disclaimer', verbose_name='resolve the sender')),
                ('resolve_sender_fail', models.BooleanField(default=False, help_text='Stop the action if the sender cannot be resolved.', verbose_name='fail when unable to resolve sender')),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'Action',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DirectoryServer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of this action.', max_length=255, verbose_name='name')),
                ('description', models.TextField(help_text='The description of this action.', verbose_name='description', blank=True)),
                ('enabled', models.BooleanField(default=True, help_text='Is this directory server enabled?', verbose_name='enabled')),
                ('base_dn', models.CharField(help_text='The LDAP base dn.', max_length=255, verbose_name='base-dn')),
                ('auth', models.SmallIntegerField(default=0, help_text='Authentication method to connect to the server', verbose_name='auth-method', choices=[(0, 'None'), (1, 'Simple')])),
                ('userdn', models.CharField(default=b'', help_text='DN of the user to authenticate with', max_length=255, verbose_name='user-DN', blank=True)),
                ('password', models.CharField(default=b'', help_text='Password to authenticate with', max_length=255, verbose_name='password', blank=True)),
                ('search_query', models.TextField(default=b'mail=%s', help_text='A search query to run against the directory server to fetch the ldap object when resolving. %s will be replaced when resolving.', verbose_name='search query')),
                ('enable_cache', models.BooleanField(default=True, help_text='Enable the LDAP query cache for this directory server', verbose_name='enable cache')),
                ('cache_timeout', models.SmallIntegerField(default=3600, help_text='How long (in seconds) a query is cached', verbose_name='cache timeout')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DirectoryServerURL',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(help_text='URL of the directory server. For example: ldap://ldapserver:389/ or ldaps://ldapserver/', max_length=255, verbose_name='URL')),
                ('position', models.PositiveSmallIntegerField(verbose_name='Position')),
                ('directory_server', models.ForeignKey(to='disclaimrwebadmin.DirectoryServer')),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'URL',
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
                ('text_use_template', models.BooleanField(default=True, help_text='Use template tags in the text part. Available tags are: {sender}, {recipient} and all attributes, that are provided by resolving the sender in a directory server', verbose_name='use template tags')),
                ('html_use_text', models.BooleanField(default=True, help_text='Use the contents of the text part for the html part.', verbose_name='use text part')),
                ('html', models.TextField(default=b'', help_text='A html disclaimer (if not filled, the plain text disclaimer will be used.', verbose_name='html-part', blank=True)),
                ('html_use_template', models.BooleanField(default=True, help_text='Use template tags in the html part. Available tags are: {sender}, {recipient} and all attributes, that are provided by resolving the sender in a directory server', verbose_name='use template tags')),
                ('template_fail', models.BooleanField(default=False, help_text="Don't use this disclaimer (and stop the associated action), if a template tag cannot be filled. If this is true, the template tag will be replaced with an empty string.", verbose_name="fail if template doesn't exist")),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of this requirement.', max_length=255, verbose_name='name')),
                ('description', models.TextField(help_text='The description of this requirement.', verbose_name='description', blank=True)),
                ('enabled', models.BooleanField(default=True, help_text='Is this requirement enabled?', verbose_name='enabled')),
                ('sender_ip', models.GenericIPAddressField(default=b'0.0.0.0', help_text='A filter for the IP-address of the sender server.', verbose_name='sender-IP address')),
                ('sender_ip_cidr', models.CharField(default=b'0', help_text='The CIDR-netmask for the sender ip address', max_length=2, verbose_name='netmask')),
                ('sender', models.TextField(default=b'.*', help_text='A regexp, that has to match the sender of a mail.', verbose_name='sender')),
                ('recipient', models.TextField(default=b'.*', help_text='A regexp, that has to match the recipient of a mail', verbose_name='recipient')),
                ('header', models.TextField(default=b'.*', help_text='A regexp, that has to match all headers of a mail. The headers will be represented in a key: value - format.', verbose_name='header-filter')),
                ('body', models.TextField(default=b'.*', help_text='A regexp, that has to match the body of a mail', verbose_name='body-filter')),
                ('action', models.SmallIntegerField(default=0, help_text='What to do, if this requirement is met?', verbose_name='action', choices=[(0, 'Accept rule'), (1, 'Deny rule')])),
            ],
            options={
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
            field=models.ForeignKey(to='disclaimrwebadmin.Rule'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='directory_servers',
            field=models.ManyToManyField(help_text='Which directory server(s) to use.', to='disclaimrwebadmin.DirectoryServer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='disclaimer',
            field=models.ForeignKey(help_text='Which disclaimer to use', to='disclaimrwebadmin.Disclaimer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='rule',
            field=models.ForeignKey(to='disclaimrwebadmin.Rule'),
            preserve_default=True,
        ),
    ]
