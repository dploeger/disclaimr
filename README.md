# Disclaimr - Mail disclaimer server

## Introduction

**Disclaimr** is a [milter daemon](https://www.milter.org/), that dynamically adds mail disclaimers or footers to filtered 
mails. Additionally, it includes a Django-based web administration user interface to easily let non-technical people manage the
 disclaimers.
 
It has the following features:

* Easy to use (and role-based) web user interface to allow non-technical staff to modify disclaimers
* Add disclaimers to the body of incoming emails or replace tags inside the body with disclaimer texts
* Support for differentiating between plaintext and HTML-mails
* Support for resolving the sender of the incoming mails and use their data from an LDAP-server dynamically inside a disclaimer

## Requirements

* [Python 2.7](https://www.python.org)
* [python-libmilter](https://github.com/crustymonkey/python-libmilter)
* [python-netaddr](https://github.com/drkjam/netaddr)
* [Django 1.7](https://www.djangoproject.com/)
* [Grappelli](http://grappelliproject.com/)
* [Python-LDAP](http://www.python-ldap.org/)
* [mysqldb](https://github.com/farcepest/MySQLdb1) (or another database backend for Python. Disclaimr doesn't support Sqlite)

## Installation

### Python packages

Install Disclaimr using pip or easy_install with the package disclaimr:

    pip install disclaimr

That will also install all most of the requirements noticed above. You still need to install the python package for the 
database backend you'd like to use. For example, to use mysqldb run:

    pip install mysql-python

### Database setup

Create a database in your preferred backend and configure it by copying the file "db.conf.dist" to "db.conf" inside the 
settings subdirectory and modify it according to your backend.

To initialize the database, run 

    python manage.py migrate

### Creating a superuser

To create an initial superuser to access the Disclaimr Frontend, use

    python manage.py createsuperuser

## Usage

Disclaimr can run from any server meeting the above requirements. Just start the disclaimr milter and configure your mail 
server to use it. For optimal performance, though, it's better to run Disclaimr directly from your mail server.

To start the milter, run

    python disclaimr.py

Disclaimr will run on localhost, Port 5000 per default. You can specify another socket-option using

    python disclaimr.py -s <socket-option>

For example "inet:localhost:6000" to use Port 6000 instead of 5000.

Run disclaimr.py with --help for more information.

## Administration

Disclaimr comes with its own web frontend based on Django. You can use the Django testserver by running

    python manage.py runserver

It's recommended to use a "real" web server and also use TLS-Encryption instead of the testserver. Please see [Django 
deployment options](https://docs.djangoproject.com/en/1.6/howto/deployment/) for more detail.

### Introduction

Disclaimr's configuration database is based on the following objects:

* Disclaimer: A disclaimer is a text, which can be used in an action. A plaintext- and an HTML-part can be configured.
* Rules: Rules are a combined set of requirements and actions.
  * Requirments: Requirements decide, wether a connection to the milter daemon will enable the actions of the rule. If one of 
  the requirements fail, the rule will be disabled. Also, there has to be at least one requirement set to "Allow" for the rule to 
  be taken into account. 
  * Actions: Actions do something with the body of the incoming mail. They can for example add a disclaimer to the body or 
  replace a tag inside the body with the disclaimer text.
* Directory Servers: If you'd like to use the resolver feature, you use directory server-objects to connect to an LDAP server

Every object contains a "name" and an optional "description" field to identify it.

## Disclaimers

Disclaimers are the configuration objects, which will be merged with the body of an incoming mail. You can configure texts for 
plaintext- and HTML-mails (or use the plaintext-value also for HTML-mails). Additionally, you can use tags inside the text, 
which will be replaced by dynamic data based on the incoming mail.

* Text-part: The disclaimer text for plaintext-mails
  * Use template tags: Parse the plaintext-disclaimer for resolver-tags (see below)
* Use text part: Instead of using the text inside the "Html-part"-field, use the text of the plaintext-field also for HTML-mails
* Html-part: The disclaimer text for HTML-mails
  * Use template tags: Parse the HTML-disclaimer for resolver-tags (see below)
* Fail if template doesn't exist: If a tag from the resolver feature cannot be replaced, this disclaimer will not be used. If 
this is not enabled, the tag will be removed with an empty string

## Rules

Rules are the basic building blocks of the milter workflow. The requirements will be checked and, if no requirement fails, 
the actions will be carried out.

### Requirements

* Enabled: Is this requirment enabled (if disabled, the requirement will be skipped)
* Sender-IP address/Netmask: An IP-Address and CIDR-Netmask, which have to match the host connecting to the milter
* Sender: A regexp, which has to match the "MAIL FROM"-Envelope
* Recipient: A regexp, which has to match the "RCPT TO"-Envelope
* Header-filter: A regexp, which has to match the complete headers of the incoming mail
* Body-filter: A regexp, which has to match the complete body of the incoming mail (the body is a text containing all mime-parts
 of the mail)
* Action: If the different matches succed, will this requirement accept the rule or deny (disable) it?

### Actions

* Action: What should be done with the mail body. Currently these actions are supported:
  * Add the disclaimer to the body
  * Replace the regexp in the field "Action parameters" with the disclaimer
* Mime type: Use this action only for bodies of this mime type
* Action parameters: Additional parameters for the selected action
* Resolve the sender: Use the resolver feature and try to resolve the "MAIL FROM"-envelope
* Fail when unable to resolve sender: If the sender can not be resolved, don't apply the action
* Disclaimer: Choose the disclaimer to use

## Directory servers

* Base-dn: The LDAP base dn
* Auth-Method: The authentication method to use when connecting to the directory server. Currently supported methods are:
  * None: Do not authenticate at all, use a guest access
  * Simple: Use simple authentication
* User-DN: User-DN to authenticate with
* Password: Password to authenticate with
* Search-Query: A query to search for when resolving an email-address. The tag {email} will be replaced with the address while
 resolving
* URLs: One or more URLs to connect to this directory server. They will be used in the order you specify if one cannot be 
contacted

## Resolver feature

Disclaimr can also be used to generate dynamic signatures. For this to work, in most cases it has to have access to the contact
 data of the sender of the email. For this purpose, Disclaimr can connect to an LDAP-server and retrieve the data based on the 
 sender-emailaddress.

If this succeeds, it can dynamically replace tags inside the disclaimer with LDAP fields.

These tags can be used in a disclaimer in any case:

* {sender}: the "MAIL FROM"-envelope value
* {recipient}: the "RCPT TO"-envelope value
* {header["key"]}: A Header with the key "key"

The following tag will be accesible when the resolver succeeds:

* {resolver["key"]}: The value of the LDAP-property "key" from the resolver
