# Disclaimr - Mail disclaimer server

## Introduction

**Disclaimr** is a [milter daemon](https://www.milter.org/), that dynamically
adds mail disclaimers (also called footers) to filtered mails.

It uses [Django](https://www.djangoproject.com/) for database abstraction and
 to present an easy-to-use web UI for non-technical staff.

It has the following features:

* Easy to use (and role-based) web user interface to allow non-technical staff
  to modify disclaimers
* Add disclaimers to the body of incoming emails or replace tags inside the
  body with disclaimer texts
* Support for differentiating between plaintext and HTML-mails
* Support for resolving the sender of the incoming mails and use their data
  from an LDAP-server dynamically inside a disclaimer
* Support for encrypted mails (S/MIME, PGP)

## Requirements

* [Python 2.7](https://www.python.org)
* [python-libmilter](https://github.com/crustymonkey/python-libmilter)
* [python-netaddr](https://github.com/drkjam/netaddr)
* [Django 1.7](https://www.djangoproject.com/)
* [Grappelli](http://grappelliproject.com/)
* [Python-LDAP](http://www.python-ldap.org/)
* [lxml](http://lxml.de/)
* [Django-admin-sortable](https://github.com/iambrandontaylor/django-admin-sortable) and [Django-admin-sortable2](https://github.com/jrief/django-admin-sortable2)
* [mysqldb](https://github.com/farcepest/MySQLdb1) (or another database
  backend for Python. Disclaimr doesn't support Sqlite)

## Installation

### Python packages

Make sure you have these dependancies installed:

* python-devel
* openldap-devel

Install the requirements of Disclaimr (for example using pip):

    pip install python-libmilter netaddr django django-grappelli python-ldap lxml django-admin-sortable django-admin-sortable2
You still need to install the python package for the database backend you'd
like to use. For example, to use MySQL with the mysqlclient API driver, run:

    pip install mysqlclient

Download the latest Disclaimr release and put it in an accessible path.

### Database setup

Create a database in your preferred backend, e.g. for MariaDB:

1. Secure your installation

	mysql\_secure\_installation
	
2. Create the database (e.g. disclaimr)

	CREATE DATABASE disclaimr;
	
3. Create a user (e.g. disclaimr) with password (e.g. disclaimr)

	CREATE USER 'disclaimr'@'localhost' IDENTIFIED BY 'disclaimr';
	
4. Grant the user access to the database

	GRANT ALL PRIVILEGES ON disclaimr.* TO 'disclaimr'@'localhost';

5. Reload the privileges table

	FLUSH PRIVILEGES;

And configure it by copying the file "db.conf.dist" to "db.conf" inside the settings
 subdirectory and modify it according to your backend.

To initialize the database, run 

    python manage.py migrate

### Creating a superuser

To create an initial superuser to access the Disclaimr Frontend, use

    python manage.py createsuperuser

## Usage

Disclaimr can run from any server meeting the above requirements. Just start
the disclaimr milter and configure your mail
server to use it. For optimal performance, though, it's better to run Disclaimr
directly from your mail server.

To start the milter, run

    python disclaimr.py

Disclaimr will run on localhost, Port 5000 per default. You can specify
another socket-option using

    python disclaimr.py -s <socket-option>

For example "inet:localhost:6000" to use Port 6000 instead of 5000.

If you'd like to use the resolver feature with an SSL-enabled LDAP-server,
that has no proper certificate, you'll have to add the "--ignore-cert" option
 to the daemon.

Run disclaimr.py with --help for more information.

>Pro Tip: You can even run the milter as a (systemd) daemon, look in the Wiki for requirments and a example script.

## Administration

Disclaimr comes with its own web frontend based on Django. You can use the
Django testserver by running:

    python manage.py runserver

You can change the socket to run the (test) server on by appending ip:port (e.g. 0:8000) to the call

	python manage.py runserver 0:8000

It's recommended to use a "real" web server and also use TLS-Encryption
instead of the testserver. Please see [Django deployment options]
(https://docs.djangoproject.com/en/1.6/howto/deployment/) for more detail.

### Introduction

Disclaimr's configuration database is based on the following objects:

* Disclaimer: A disclaimer is a text, which can be used in an action. A
  plaintext- and an HTML-part can be configured.
* Rules: Rules are a combined set of requirements and actions. Each rule will
 be checked in the order they are sorted in. The action of the first rule
 matching will be carried out (as long as the "continue" flag of the rule
 isn't checked)
  * Requirements: Requirements decide, wether a connection to the milter
    daemon will enable the actions of the rule. If one of
    the requirements fail, the rule will be disabled. Also, there has to be at
    least one requirement set to "Allow" for the rule to be taken into account.
  * Actions: Actions do something with the body of the incoming mail.
    They can for example add a disclaimer to the body or replace a tag inside
     the body with the disclaimer text.
* Directory Servers: If you'd like to use the resolver feature, you use
  directory server-objects to connect to an LDAP server

Every object contains a "name" and an optional "description" field to
identify it. There are additional fields to configure as follows:

## Disclaimers

Disclaimers are the configuration objects, which will be merged with the
body of an incoming mail. You can configure texts for plaintext- and
HTML-mails (or use the plaintext-value also for HTML-mails). Additionally,
you can use tags inside the text, which will be replaced by dynamic data
based upon the incoming mail.

* Text-part: The disclaimer text for plaintext-mails
  * Use template tags: Parse the plaintext-disclaimer for resolver-tags
    (see below)
* Use text part: Instead of using the text inside the "Html-part"-field,
  use the text of the plaintext-field also for HTML-mails
* Html-part: The disclaimer text for HTML-mails
  * Use template tags: Parse the HTML-disclaimer for resolver-tags (see below)
* Fail if template doesn't exist: If a tag from the resolver feature cannot be
  replaced, this disclaimer will not be used. If this is not enabled, the tag
   will be removed with an empty string
* Use HTML as a fallback: If the incoming mail only contains mime-parts that
  aren't either text or HTML, Disclaimr will use the text disclaimer per
  default. If you check this option, Disclaimr will instead use the HTML
  disclaimer.

## Rules

Rules are the basic building blocks of the milter workflow. The requirements
will be checked and, if no requirement fails, the actions will be carried out
 in the order they are sorted in the web ui.

The order the rules will be carried out can also be changed using the web ui.

If the additional parameter "Continue after this rule" is checked, additional
 matching rules, will be carried out after this rule.

### Requirements

* Enabled: Is this requirment enabled? (if disabled, the requirement will be
  skipped)
* Sender-IP address/Netmask: An IP-Address and CIDR-Netmask, which have to
  match the host connecting to the milter
* Sender: A regexp, which has to match the "MAIL FROM"-Envelope
* Recipient: A regexp, which has to match the "RCPT TO"-Envelope
* Header-filter: A regexp, which has to match the complete headers of the
  incoming mail
* Body-filter: A regexp, which has to match the complete body of the incoming
  mail (the body is a text containing all mime-parts of the mail)
* Action: If the different matches succed, will this requirement accept the
  rule or deny (disable) it?

### Actions

* Action: What should be done with the mail body. Currently these actions are
  supported:
  * Add the disclaimer to the body
  * Replace the regexp in the field "Action parameters" with the disclaimer
  * Add the disclaimer to the body by adding another MIME-part to it and
    adding the orignal mail as a mime/rfc-822-part (useful for
    encrypted/signed E-Mails)
* Mime type: Use this action only for bodies of this mime type
* Action parameters: Additional parameters for the selected action
* Resolve the sender: Use the resolver feature and try to resolve the
  "MAIL FROM"-envelope
* Fail when unable to resolve sender: If the sender can not be resolved,
  don't apply the action
* Disclaimer: Choose the disclaimer to use

## Directory servers

* Base-dn: The LDAP base dn
* Auth-Method: The authentication method to use when connecting to the
  directory server. Currently supported methods are:
  * None: Do not authenticate at all, use a guest access
  * Simple: Use simple authentication
* User-DN: User-DN to authenticate with
* Password: Password to authenticate with
* Search-Query: A query to search for when resolving an email-address. The
  tag %s will be replaced with the address while resolving
* URLs: One or more URLs to connect to this directory server. They will be
  used in the order you specify if one cannot be contacted

## Resolver feature

Disclaimr can also be used to generate dynamic footers. For this to work,
in most cases it has to have access to the contact data of the sender of the
email. For this purpose, Disclaimr can connect to an LDAP-server and retrieve
the data based on the sender-emailaddress.

If this succeeds, it can dynamically replace tags inside the disclaimer with
LDAP fields.

These tags can be used in a disclaimer in any case:

* {sender}: the "MAIL FROM"-envelope value
* {recipient}: the "RCPT TO"-envelope value
* {header["key"]}: A mail header with the key "key"

The following tag will be accesible when the resolver succeeds:

* {resolver["key"]}: The value of the LDAP-property "key" from the resolver

Since v1.0-rc2 you can even decide what to do if the resolver fails:

* {rt}I get removed if {resolver["key"]} fails{/rt}: If the LDAP-property "key"
 has no value everything (including the surrounding tags) will be removed

## Supporting Encryption

Encrypted mails (either using PGP or S/MIME) are a problem when you like to
centrally manage disclaimers or footers. As the text of the mails are
encrypted, you cannot look into it to replace tags with dynamic footers. When
 the mails are signed, you also cannot just add text, because that would
 break the signature.

What you *can* do, is add another mime part to it. The basic workflow of
supporting encryption while maintaining a dynamic footer is:

* Generate the disclaimer as a separate mime-part
* Convert the original mime-part to a rfc822-part ("an attached message")
* Build a multipart-mail with both parts attached

To identify pgp or mime parts, you can use the following methods:

### Detecting PGP

To detect pgp, add a requirement, that matches the body for the following
regexp:

    BEGIN PGP SIGNED MESSAGE|BEGIN PGP MESSAGE

### Detecting S/MIME

To detect an S/MIME-mail use a requirement with a header filter and this regexp:

    application/pkcs7-signature|application/pkcs7-mime
