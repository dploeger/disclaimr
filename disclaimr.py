""" disclaimr - Mail disclaimer server
"""
import argparse
import email
import ldap
from lxml import etree
import os
import re

import libmilter as lm
import signal
import traceback
import sys
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

        """ Initialize the milter

        :param opts: SMFIF-options for this milter
        :param protos: SMFIP-options for this milter
        :return: The milter
        """

        lm.MilterProtocol.__init__(self, opts, protos)
        lm.ForkMixin.__init__(self)

        self.mail_data = {
            "headers": [],
            "headers_dict": {},
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

            logging.debug("Got part of content-type %s" % mail.get_content_type())

            # Set disclaimer text

            logging.debug("Setting disclaimer text")

            if mail.get_content_type().lower() == "text/plain":

                text = action.disclaimer.text.encode("utf-8", "replace")

                do_replace = action.disclaimer.text_use_template

            elif action.disclaimer.html_use_text:

                text = ("<p>%s</p>" % action.disclaimer.text).encode("utf-8", "replace")

                do_replace = action.disclaimer.text_use_template

            else:

                text = action.disclaimer.html.encode("utf-8", "replace")

                do_replace = action.disclaimer.html_use_template

            if do_replace:

                logging.debug("Building replacement dictionary")

                # Basic replacement dictionary

                replacements = {
                    "sender": self.mail_data["envelope_from"],
                    "recipient": self.mail_data["envelope_rcpt"],
                    "header": self.mail_data["headers_dict"],
                    "resolver": {}
                }

                if action.resolve_sender:

                    # Fill resolver dictionary

                    logging.info("Connecting to directory server")

                    resolved_successfully = False

                    for directory_server in models.DirectoryServer.objects.all():

                        for url in directory_server.directoryserverurl_set.all():

                            logging.debug("Trying url %s" % url.url)

                            conn = ldap.initialize(url.url)

                            if directory_server.auth == constants.DIR_AUTH_SIMPLE:

                                try:

                                    conn.simple_bind_s(directory_server.userdn, directory_server.password)

                                except ldap.SERVER_DOWN:

                                    # Cannot reach server. Skip.

                                    logging.warn("Cannot reach server %s. Skipping." % url)

                                    continue

                                except (ldap.INVALID_CREDENTIALS, ldap.INVALID_DN_SYNTAX):

                                    # Cannot authenticate. Skip.

                                    logging.warn("Cannot authenticate to directory server %s with dn %s. Skipping." % (
                                        url,
                                        directory_server.userdn)
                                    )

                                    continue

                            try:

                                result = conn.search_s(
                                    directory_server.base_dn,
                                    ldap.SCOPE_SUBTREE,
                                    directory_server.search_query % self.mail_data["envelope_from"]
                                )

                            except ldap.SERVER_DOWN:

                                # Cannot reach server. Skip.

                                logging.warn("Cannot reach server %s. Skipping." % url)

                                continue

                            except ldap.INVALID_CREDENTIALS:

                                # Cannot authenticate as guest. Skip.

                                logging.warn("Cannot authenticate to directory server %s as guest. Skipping." % url)

                                continue

                            if not result:

                                if action.resolve_sender_fail:

                                    logging.warn("Cannot resolve email %s. Skipping" % self.mail_data["envelope_from"])

                                    return

                                logging.info("Cannot resolve email %s" % self.mail_data["envelope_from"])

                            elif len(result) > 1:

                                logging.warn("Multiple results found for email %s. Using the first one." %
                                             self.mail_data["envelope_from"])

                            # Flatten result into replacement dict

                            logging.debug("Found entry %s" % result[0][0])

                            resolved_successfully = True

                            for key in result[0][1].iterkeys():

                                replacements["resolver"][key.lower()] = ",".join(result[0][1][key])

                    if not resolved_successfully and action.resolve_sender_fail:

                        logging.warn("Cannot resolve email %s. Skipping" % self.mail_data["envelope_from"])

                        return

                # Replace template text

                logging.debug("Replacing template text")

                # A template {key}

                template = re.compile("\{([^}]*)\}")

                # A template referring to a dictionary: {key["test"]}

                subkey_template = re.compile("^([^\[]*)\[\"([^\"]*)\"\]$")

                while True:

                    # Search for template strings

                    match = template.search(text)

                    if not match:

                        # No more template strings

                        break

                    key = match.groups()[0].lower()

                    logging.debug("Replacing key %s" % key)

                    replace_key = match.groups()[0]

                    # Is this key a dictionary-key?

                    dictmatch = subkey_template.search(key)

                    if dictmatch:

                        # Yes. Resolve that

                        key = dictmatch.groups()[0].lower()
                        subkey = dictmatch.groups()[1].lower()

                        if key in replacements and subkey in replacements[key]:

                            value = replacements[key][subkey]

                        elif action.disclaimer.template_fail:

                            # We cannot resolve the key. Fail.

                            logging.warn("Cannot resolve key %s. Skipping" % key)

                            return

                        else:

                            logging.info("Cannot resolve key %s" % key)

                            value = ""

                    else:

                        if key in replacements:

                            value = replacements[key]

                        elif action.disclaimer.template_fail:

                            # We cannot resolve the key. Fail.

                            logging.warn("Cannot resolve key %s. Skipping" % key)

                            return

                        else:

                            logging.info("Cannot resolve key %s" % key)

                            value = ""

                    text = text.replace("{%s}" % replace_key, value)

            # Optionally convert the text back to the mail's charcode

            dest_charset = mail.get_charset()

            if dest_charset:

                text = dest_charset.convert(text)

            # Carry out the action

            logging.debug("Adding Disclaimer %s to body" % action.disclaimer.name)

            if mail.get_content_type().lower() == "text/plain":

                if action.action == constants.ACTION_ACTION_ADD:

                    # text/plain can simply be added

                    mail.set_payload("%s\n%s" % (mail.get_payload(), text))

                elif action.action == constants.ACTION_ACTION_REPLACETAG:

                    # text/plain can simply be replaced

                    mail.set_payload(re.sub(action.action_parameters, text, mail.get_payload()))

            elif mail.get_content_type().lower() == "text/html":

                # text/html has to been put before the closing body-tag, so parse the text

                html_part = etree.HTML(mail.get_payload())

                disclaimer_part = etree.HTML(text)

                if action.action == constants.ACTION_ACTION_ADD:

                    if len(html_part.xpath("body")) > 0:

                        # Add the new part inside the existing body-tag

                        html_part.xpath("body")[0].append(disclaimer_part.xpath("body")[0].getchildren()[0])

                    else:

                        # No body found. Just add the new part

                        html_part.append(disclaimer_part.xpath("body")[0].getchildren()[0])

                    mail.set_payload(etree.tostring(html_part, pretty_print=True, method="html"))

                elif action.action == constants.ACTION_ACTION_REPLACETAG:

                    # For replacing, we'll just replace tag in the plain html string with the disclaimer html string

                    mail.set_payload(re.sub(action.action_parameters, etree.tostring(disclaimer_part.xpath("body")[
                        0].getchildren()[0]), mail.get_payload()))

    @lm.noReply
    def connect(self, hostname, family, ip, port, cmd_dict):

        """ Called when a client connects to the milter

        :param hostname: Hostname of the client
        :param family: IPv4 or IPv6 connect?
        :param ip: IP of the client
        :param port: Source-port of the connection
        :param cmd_dict: A libmilter command dictionary
        :return:
        """

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

        """ Called when the MAIL FROM-envelope has been sent

        :param addr: The MAIL FROM-envelope value
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

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

        """ Called when the RCPT TO-envelope has been set

        :param recip: The RCPT TO-envelope
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

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

        """ Called when a header is received

        :param key: The header key
        :param val: The header value
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("HEADER: %s: %s" % (key, val))

        self.mail_data["headers_dict"][key.lower()] = val
        self.mail_data["headers"].append("%s: %s" % (key, val))

        return lm.CONTINUE

    @lm.noReply
    def eoh(self, cmd_dict):

        """ Called, when all headers were sent

        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

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

        """ Called when a body chunk has been received

        :param chunk: A chunk of the body
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.enabled:

            return lm.CONTINUE

        logging.debug("BODY: (chunk) %s" % chunk)

        # Requirement will be checked in eob

        self.mail_data["body"] += chunk

        return lm.CONTINUE

    def eob(self, cmd_dict):

        """ Called when all body chunks have been received

        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

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

            elif req.rule.id not in rules_blacklist and req.rule.id not in rules:

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

        """ Called, when a connection with a client is closed
        """

        logging.debug("Close called. QID: %s" % self._qid)


def run_disclaimr_milter():

    """ Start the multiforking milter daemon
    """

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

    parser.add_argument("-i", "--ignore-cert", dest="ignore_cert", action="store_true",
                        help="Ignore certificates when connecting to tls-enabled directory servers"
    )

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

    if options.ignore_cert:

        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

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
