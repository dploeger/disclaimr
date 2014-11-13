# Disclaimr - Mail disclaimer server

## Introduction

**Disclaimr** is a [milter daemon](https://www.milter.org/), that dynamically adds mail disclaimers or footers to filtered mails.
 It can solve the following problems:

* Centrally define company email footers following certain conventions
* Enable email marketing features in email-footers

## Requirements

* [Python 2.7](https://www.python.org)
* [python-libmilter](https://github.com/crustymonkey/python-libmilter)
* [python-netaddr](https://github.com/drkjam/netaddr)
* [Django 1.7](https://www.djangoproject.com/)
* [Grappelli](http://grappelliproject.com/)
* [mysqldb](https://github.com/farcepest/MySQLdb1) (or another database backend for Python. Disclaimr doesn't support Sqlite)

## Installation

Disclaimr can run from any server meeting the above requirements. Just start the disclaimr milter and configure your mail 
server to use it. For optimal performance, though, it's better to run Disclaimr directly from your mail server. 

## Administration

Disclaimr uses a Sqlite database for configuration of rules and disclaimers. To make it easier, 
a simple Django-based web application named Disclaimrweb is provided.

TODO: Make a script to set that up.
