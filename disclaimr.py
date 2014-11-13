""" disclaimr - Mail disclaimer server
"""
import argparse
import email
from lxml import etree
import os
import re

import libmilter as lm
import signal
import traceback
import sys
from string import Template
import logging

# Setup Django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "disclaimrweb.settings")
import django
django.setup()

from disclaimrwebadmin import models
from disclaimrwebadmin import constants


class DisclaimrMilter(lm.ForkMixin, lm.MilterProtocol):

    """ Disclaimr Milter

    This is the main milter thread for disclaimr based on libmilter.MiterProtocol. It will be given the options and a basic
    configuration set. During its workflow, it will narrow down the available requirements and disable itself,
    once no requirements are left, so that no unneccesary steps are taken.

    """

    def __init__(self, opts=0, protos=0):

        lm.MilterProtocol.__init__(self, opts, protos)
        lm.ForkMixin.__init__(self)

        self.mail_data = {
            "headers": [],
            "body": ""
        }

        self.enabled = True

        self.options = options

        self.requirements = []

        self.actions = []

        self.configuration = configuration

        logging.debug("Initialising Milter Fork")

    def do_action(self, mail, action):

        """
        Apply an action on a mail (optionally recursing through the different mail payloads)

        :param mail: A mail object
        :param action: The action to carry out
        :return: The modified mail
        """

        if mail.is_multipart():

            for payload in mail.get_payload():

                self.do_action(payload, action)

        else:

            text = ""

            # TODO Optionally try to resolve and fill out parameters

            # Carry out the action

            logging.debug("Adding Disclaimer %s to body" % action.disclaimer.name)

            if mail.get_content_type().lower() == "text/plain":

                text = action.disclaimer.text

                if action.action == constants.ACTION_ACTION_ADD:

                    # text/plain can simply be added

                    mail.set_payload("%s\n%s" % (mail.get_payload(), action.disclaimer.text))

                elif action.action == constants.ACTION_ACTION_REPLACETAG:

                    # TODO

                    pass

            elif mail.get_content_type().lower() == "text/html":

                # text/html has to been put before the closing body-tag, so parse the text

                html_part = etree.HTML(mail.get_payload())

                if action.disclaimer.html_use_text:

                    text = "<p>%s</p>" % action.disclaimer.text

                else:

                    text = action.disclaimer.html

                add_part = etree.HTML(text)

                if action.action == constants.ACTION_ACTION_ADD:

                    html_part.xpath("body")[0].append(add_part.xpath("body")[0].getchildren()[0])

                    mail.set_payload(etree.tostring(html_part, pretty_print=True, method="html"))

                elif action.action == constants.ACTION_ACTION_REPLACETAG:

                    # TODO

                    pass


    @lm.noReply
    def connect(self, hostname, family, ip, port, cmd_dict):

        logging.debug("CONNECT: %s, %s, %s, %s" % (hostname, family, ip, port))

        self.mail_data["sender_ip"] = ip

        # Check for IP-requirements

        for sender_ip in self.configuration["sender_ip"]:

            if ip in sender_ip["ip"]:

                logging.debug("Found IP in a requirement.")

                if not sender_ip["id"] in self.requirements:

                    self.requirements.append(sender_ip["id"])

        if len(self.requirements) == 0:

            logging.debug("Couldn't find the IP in any requirement. Skipping.")

            self.enabled = False

        return lm.CONTINUE

    @lm.noReply
    def mailFrom(self, addr, cmd_dict):

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("MAILFROM: %s" % addr)

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.match(req.sender, addr):

                self.requirements = filter(lambda x: x != req.id, self.requirements)

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the sender address in any requirement. Skipping.")

            self.enabled = False

        self.mail_data["envelope_from"] = addr

        return lm.CONTINUE

    @lm.noReply
    def rcpt(self, recip, cmd_dict):

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("RCPT: %s" % recip)

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.match(req.recipient, recip):

                self.requirements = filter(lambda x: x != req.id, self.requirements)

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the recipient address in any requirement. Skipping.")

            self.enabled = False

        self.mail_data["envelope_rcpt"] = recip

        return lm.CONTINUE

    @lm.noReply
    def header(self, key, val, cmd_dict):

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("HEADER: %s: %s" % (key, val))

        self.mail_data["headers"].append("%s: %s" % (key, val))

        return lm.CONTINUE

    @lm.noReply
    def eoh(self, cmd_dict):

        if not self.enabled:

            return lm.CONTINUE

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.match(req.header, "\n".join(self.mail_data["headers"])):

                self.requirements = filter(lambda x: x != req.id, self.requirements)

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the header in any requirement. Skipping.")

            self.enabled = False

        return lm.CONTINUE

    @lm.noReply
    def body(self, chunk, cmd_dict):

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("BODY: (chunk) %s" % chunk)

        # Requirement will be checked in eob

        self.mail_data["body"] += chunk

        return lm.CONTINUE

    def eob(self, cmd_dict):

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("ENDOFBODY: Processing actions...")

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.match(req.body, self.mail_data["body"]):

                self.requirements = filter(lambda x: x != req.id, self.requirements)

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the body in any requirement. Skipping.")

            self.enabled = False

            return lm.CONTINUE

        # Filter out denied rules

        rules_blacklist = []

        rules = []

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if req.action == constants.REQ_ACTION_DENY:

                rules_blacklist.append(req.rule.id)

            elif req.rule.id not in rules_blacklist and not req.rule.id in rules:

                rules.append(req.rule.id)

        # Transform body into a mime mail to work on it

        mail = email.message_from_string("%s\n%s" % ("\n".join(self.mail_data["headers"]), self.mail_data["body"]))

        # Carry out the actions

        for rule in models.Rule.objects.filter(id__in=rules):

            for action in rule.action_set.all():

                if not action.enabled:

                    continue

                logging.info("Carrying out action %s of rule %s" % (action.name, rule.name))

                self.do_action(mail, action)

        # Replace the body with the modified one

        # Remove headers

        mail_keys = mail.keys()

        content_type_header = ""

        for key in mail_keys:

            # email.message still needs the content type for the as_string-method

            if not key.lower() == "content-type":

                del mail[key]

            else:

                content_type_header = "%s: %s\n" % (key, mail[key])

        new_body = mail.as_string()

        # Now, remove the content-type to have the right body again

        new_body = re.sub(content_type_header, "", new_body)

        self.replBody(new_body)

        return lm.CONTINUE

    def close(self):
        logging.debug("Close called. QID: %s" % self._qid)


def run_disclaimr_milter():

    # We can set our milter opts here
    opts = lm.SMFIF_CHGBODY | lm.SMFIF_CHGFROM | lm.SMFIF_ADDRCPT | lm.SMFIF_QUARANTINE

    # We initialize the factory we want to use (you can choose from an
    # AsyncFactory, ForkFactory or ThreadFactory.  You must use the
    # appropriate mixin classes for your milter for Thread and Fork)
    f = lm.ForkFactory(options.socket, DisclaimrMilter, opts)

    def signal_handler(num, frame):
        f.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # run it
        f.run()

    except Exception, e:

        f.close()

        print >> sys.stderr, 'EXCEPTION OCCURED: %s' % e

        traceback.print_tb(sys.exc_traceback)

        sys.exit(3)

if __name__ == '__main__':

    # Argument handling

    parser = argparse.ArgumentParser(description="Disclaimr - Mail disclaimer server. Starts a milter daemon, "
                                                 "that adds dynamic disclaimers to messages")

    parser.add_argument("-s", "--socket", dest="socket", default="inet:127.0.0.1:5000",
                        help="Socket to open. IP-Sockets need "
                             "to be in the form inet:<ip>:<port> [inet:127.0.0.1:5000]")

    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", help="Be quiet doing things")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", help="Enable debug logging")

    options = parser.parse_args()

    if options.quiet and options.debug:
        parser.error("Cannot specify debug and quiet at the same time.")

    # Setup logging

    if options.quiet:
        logging.basicConfig(level=logging.ERROR)
    elif options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Starting disclaimr")

    # Fetch basic configuration data for efficiency

    logging.debug("Generating basic configuration")

    configuration = {
        "sender_ip": []
    }

    # Fetch the sender_ip networks of all enabled requirements, that have at least one enabled action in their associated rule

    for requirement in models.Requirement.objects.all():

        if requirement.enabled:

            # Check, if all associated actions are enabled

            enabled_actions = requirement.rule.action_set.count()

            for test_action in requirement.rule.action_set.all():

                if not test_action.enabled:

                    enabled_actions -= 1

            if enabled_actions > 0:

                # There are some enabled actions.

                configuration["sender_ip"].append({

                    "ip": requirement.get_sender_ip_network(),
                    "id": requirement.id

                })

    # Run Disclaimr

    run_disclaimr_milter()
