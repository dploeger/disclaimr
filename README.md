# Disclaimr - Mail disclaimer server

## Introduction

**Disclaimr** is a [milter daemon](https://www.milter.org/), that dynamically adds mail disclaimers or footers to filtered mails.
 It can solve the following problems:

* Centrally define company email footers following certain conventions
* Enable email marketing features in email-footers

## Requirements

* [python-libmilter](https://github.com/crustymonkey/python-libmilter)
* [Python 2.7](https://www.python.org)

## Installation

Disclaimr can run from any server meeting the above requirements. Just start the disclaimr milter and configure your mail 
server to use it. For optimal performance, though, it's better to run Disclaimr directly from your mail server. 

## Administration

Disclaimr uses a Sqlite database for configuration of rules and disclaimers. To make it easier, 
a simple Django-based web application named Disclaimrweb is provided.

To use it, install [Django](https://www.djangoproject.com). Mostly this is as easy as running

    pip install django

on your server. After that, create a django project by running

    django-admin startproject <project-name> <project-path>

Afterwards, copy the disclaimrweb directory into the specified project path and add "disclaimrweb" to the variable 
INSTALLED_APPS in <project-path>/<project-name>/settings.py.

Then you can go to <project-path> and run

    python manage.py migrate

This will ask you for a superuser name and password and build up an initial database (you'll have to use that database when 
configuring the milter daemon). 

    python manage.py runserver 0.0.0.0:8000

to start the Django web server on port 8000. After that you can connect to disclaimrweb by going to

    http://<django-server>:8000/admin

**Note**: This will use the Django development server, which isn't quite suitable for production environments. It's better to 
deploy [Django using WSGI](https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/).