""" Python Module for class MilterHelper """
import base64
import copy
import email
import logging
import quopri
import ldap
from lxml import etree
import re
from disclaimr.query_cache import QueryCache
from disclaimrwebadmin import models, constants


class MilterHelper(object):

    """ A helper class, that is used by the milter daemon to do the actual work.
    """

    def __init__(self, configuration):

        """ Init the helper

        The configuration dictionary currently has to hold the following keys:

        sender_ip: A list of dictionaries with the ip-sender requirements and
                the requirement id

        :param configuration: A configuration dictionary
        :return:
        """

        self.configuration = configuration

        self.mail_data = {
            "headers": [],
            "headers_dict": {},
            "body": ""
        }

        self.enabled = True

        self.requirements = []

        self.actions = []

    def connect(self, hostname, family, ip, port, cmd_dict):

        """ Called when a client connects to the milter

        :param hostname: Hostname of the client
        :param family: IPv4 or IPv6 connect?
        :param ip: IP of the client
        :param port: Source-port of the connection
        :param cmd_dict: A libmilter command dictionary
        """

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

    def mail_from(self, addr, cmd_dict):

        """ Called when the MAIL FROM-envelope has been sent

        :param addr: The MAIL FROM-envelope value
        :param cmd_dict: A libmilter command dictionary
        """

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.search(req.sender, addr):

                self.requirements = filter(
                    lambda x: x != req.id, self.requirements
                )

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the sender address in any "
                          "requirement. Skipping.")

            self.enabled = False

        self.mail_data["envelope_from"] = addr

    def rcpt(self, recip, cmd_dict):

        """ Called when the RCPT TO-envelope has been set

        :param recip: The RCPT TO-envelope
        :param cmd_dict: A libmilter command dictionary
        """

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.search(req.recipient, recip):

                self.requirements = filter(
                    lambda x: x != req.id, self.requirements
                )

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the recipient address in any "
                          "requirement. Skipping.")

            self.enabled = False

        self.mail_data["envelope_rcpt"] = recip

    def header(self, key, val, cmd_dict):

        """ Called when a header is received

        :param key: The header key
        :param val: The header value
        :param cmd_dict: A libmilter command dictionary
        """

        self.mail_data["headers_dict"][key.lower()] = val
        self.mail_data["headers"].append("%s: %s" % (key, val))

    def eoh(self, cmd_dict):

        """ Called, when all headers were sent

        :param cmd_dict: A libmilter command dictionary
        """

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.search(req.header, "\n".join(self.mail_data["headers"])):

                self.requirements = filter(
                    lambda x: x != req.id, self.requirements
                )

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the header in any "
                          "requirement. Skipping.")

            self.enabled = False

    def body(self, chunk, cmd_dict):

        """ Called when a body chunk has been received

        :param chunk: A chunk of the body
        :param cmd_dict: A libmilter command dictionary
        """

        # Requirement will be checked in eob

        self.mail_data["body"] += chunk

    def eob(self, cmd_dict):

        """ Called when all body chunks have been received

        Returns a list of dictionaries with modification tasks.
        Currently supported keys:

        "repl_body": Replace the body with the value

        :param cmd_dict: A libmilter command dictionary
        :returns: The modification list
        """

        # Check requirements

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if not re.search(req.body, self.mail_data["body"]):

                self.requirements = filter(
                    lambda x: x != req.id, self.requirements
                )

        if len(self.requirements) == 0:

            logging.debug("Couldn't match the body in any "
                          "requirement. Skipping.")

            self.enabled = False

            return

        # Filter out denied rules

        rules_blacklist = []

        rules = []

        for req in models.Requirement.objects.filter(id__in=self.requirements):

            if req.action == constants.REQ_ACTION_DENY:

                rules_blacklist.append(req.rule.id)

            if req.rule.id not in rules_blacklist\
               and req.rule.id not in rules:

                rules.append(req.rule.id)

        # Remove rules if they are in the rules black list

        tmp = []

        for rule in rules:

            if rule not in rules_blacklist:

                tmp.append(rule)

        rules = tmp

        if len(rules) == 0:

            # After checking the left over requirements, no rules were left
            # to run.

            self.enabled = False
            return

        # Transform body into a mime mail to work on it

        mail = email.message_from_string(
            "%s\n%s" % (
                "\n".join(self.mail_data["headers"]),
                self.mail_data["body"]
            )
        )

        orig_mail = copy.deepcopy(mail)

        # Carry out the actions

        for rule in models.Rule.objects.filter(id__in=rules):

            for action in rule.action_set.all():

                if not action.enabled:

                    continue

                logging.info("Carrying out action %s of rule %s" % (
                    action.name,
                    rule.name
                ))

                returned_mail = self.do_action(mail, action)

                if returned_mail is not None:

                    mail = returned_mail

            if not rule.continue_rules:

                break

        # Build workflow

        workflow = {}

        # Change headers?

        for header in mail.keys():

            if header not in orig_mail.keys():

                # Add header

                if "add_header" not in workflow:

                    workflow["add_header"] = {}

                workflow["add_header"][header] = orig_mail[header]

            elif mail[header] != orig_mail[header]:

                # Change header

                if "change_header" not in workflow:

                    workflow["change_header"] = {}

                workflow["change_header"][header] = mail[header]

        # Remove headers?

        for header in orig_mail.keys():

            if header not in mail.keys():

                if "delete_header" not in workflow:

                    workflow["delete_header"] = []

                workflow["delete_header"].append(header)

        # Remove all headers from mail, so we can safely replace the body. Do
        #  this by removing everything before the first empty line (as per RFC)

        new_body = mail.as_string()

        # Work around mails with mixed line endings. Simply use the first of
        # any line ending assuming that there's the place

        strip_place_rn = new_body.find("\r\n\r\n")
        strip_place_n = new_body.find("\n\n")

        if strip_place_n == -1:

            strip_place = strip_place_rn + 2

        elif strip_place_rn == -1:

            strip_place = strip_place_n + 2

        elif strip_place_rn < strip_place_n:

            strip_place = strip_place_rn + 2

        elif strip_place_n < strip_place_rn:

            strip_place = strip_place_n + 2

        else:

            strip_place = 0

        new_body = new_body[strip_place::]

        # Replace the body with the modified one

        workflow["repl_body"] = new_body

        return workflow

    @staticmethod
    def make_html(text):

        """
        Escape text to HTML entities

        :param text: Non-HTML-Text
        :return: HTMLized text
        """

        # Replace \r\n newlines with \n

        text = re.sub("\r\n", "\n", text)

        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
            }

        text = "".join(html_escape_table.get(c, c) for c in text)

        # Convert Newlines with br

        text = re.sub("\n", "<br />", text)

        return text

    @staticmethod
    def decode_mail(mail):

        """ Takes a email.mime.Message and decodes the payload according to
        the Content-Transfer-Encoding header

        :param mail: The message (part)
        :return: A tuple of the found encoding and the decoded payload
        """

        mail_text = mail.get_payload()

        # Decode mail text, if non-7/8-bit was used for transfer

        if "Content-Transfer-Encoding" in mail:

            encoding = mail["Content-Transfer-Encoding"].lower()

            if encoding == "quoted-printable":

                mail_text = quopri.decodestring(mail_text)

            elif encoding == "base64":

                mail_text = base64.b64decode(mail.get_payload())

            else:

                # 7 or 8 bit

                encoding = "78bit"

        else:

            encoding = "78bit"

        return encoding, mail_text

    def do_action(self, mail_parameter, action):

        """ Apply an action on a mail (optionally recursing through the
            different mail payloads)

        :param mail_parameter: A mail object
        :param action: The action to carry out
        :return: The modified mail
        """

        # We work on a copy here. Remove the reference

        mail = copy.deepcopy(mail_parameter)

        if mail.is_multipart():

            # This is a multipart, recurse through the subparts

            new_payloads = []

            for payload in mail.get_payload():

                returned_mail = self.do_action(payload, action)

                if returned_mail is not None:

                    new_payloads.append(returned_mail)

            mail.set_payload(new_payloads)

            return mail

        else:

            logging.debug(
                "Got part of content-type %s" % mail.get_content_type()
            )

            if mail.get_content_type().lower() not in ("text/plain",
                                                       "text/html")\
               and not action.action == constants.ACTION_ACTION_ADDPART:

                logging.info(
                    "Content-type %s is currently not supported for actions "
                    "other than addpart." % (
                        mail.get_content_type(),
                    )
                )

                return mail

            # Fetch the content type of the mail

            if mail.get_content_type().lower() not in ("text/plain",
                                                       "text/html") \
               and action.action == constants.ACTION_ACTION_ADDPART:

                # Cannot detect the right content type. Set the disclaimer
                # content type to the fallback type

                if action.disclaimer.use_html_fallback:

                    content_type = "text/html"

                else:

                    content_type = "text/plain"

            else:

                content_type = mail.get_content_type().lower()

            # Set disclaimer text

            logging.debug("Setting disclaimer text")

            if content_type == "text/plain":

                disclaimer_text = action.disclaimer.text

                disclaimer_charset = action.disclaimer.text_charset

                do_replace = action.disclaimer.text_use_template

            elif action.disclaimer.html_use_text:

                # Rework text disclaimer to valid html

                disclaimer_text = action.disclaimer.text

                disclaimer_charset = action.disclaimer.text_charset

                do_replace = action.disclaimer.text_use_template

            else:

                disclaimer_text = action.disclaimer.html

                disclaimer_charset = action.disclaimer.html_charset

                do_replace = action.disclaimer.html_use_template

            # Optionally recode text to match mail part encoding

            charset = mail.get_content_charset()

            if charset is None or charset == "":

                charset = "us-ascii"

            if not charset.lower() == disclaimer_charset.lower():

                if isinstance(disclaimer_text, unicode):

                    # unicode strings can directly be encoded

                    disclaimer_text = disclaimer_text.encode(
                        charset.lower(),
                        "replace"
                    )

                else:

                    # Convert string to unicode string and encode it afterwards

                    disclaimer_text = disclaimer_text.decode("utf-8").encode(
                        charset.lower()
                    )

            if do_replace:

                # The disclaimer has replacement tags. Replace them.

                logging.debug("Building replacement dictionary")

                # Basic replacement dictionary

                replacements = {
                    "sender": self.mail_data["envelope_from"],
                    "recipient": self.mail_data["envelope_rcpt"],
                    "header": self.mail_data["headers_dict"],
                    "resolver": {}
                }

                if action.resolve_sender:

                    # We should resolve the sender. Add resolver replacements
                    # to the replacement dictionary

                    resolved_successfully = False

                    for directory_server in action.directory_servers.all():

                        if not directory_server.enabled:

                            # Directory server is disabled. Skip.

                            logging.debug(
                                "Directory server %s is disabled. Skipping." %
                                directory_server.name
                            )

                            continue

                        logging.info(
                            "Connecting to directory server %s" %
                            directory_server.name
                        )

                        # The query we need to run against the directory server

                        query = directory_server.search_query % (
                            self.mail_data["envelope_from"],
                        )

                        result = None

                        # Do we have that query cached?

                        if directory_server.enable_cache:

                            # Yes. Fetch it from the cache

                            result = QueryCache.get(directory_server, query)
                            resolved_successfully = True

                        if result is None:

                            # No. Fetch it from the server

                            urls = directory_server.directoryserverurl_set.all()

                            for url in urls:

                                # Try the different URLs of the server

                                logging.debug("Trying url %s" % url.url)

                                conn = ldap.initialize(url.url)

                                ldap_user = ""
                                ldap_password = ""

                                if directory_server.auth == \
                                        constants.DIR_AUTH_SIMPLE:

                                    # The directory server needs simple auth

                                    ldap_user = directory_server.userdn
                                    ldap_password = directory_server.password

                                try:

                                    conn.simple_bind_s(
                                        ldap_user,
                                        ldap_password
                                    )

                                except ldap.SERVER_DOWN:

                                    # Cannot reach server. Skip.

                                    logging.warn(
                                        "Cannot reach server %s. "
                                        "Skipping." % url
                                    )

                                    continue

                                except (
                                    ldap.INVALID_CREDENTIALS,
                                    ldap.INVALID_DN_SYNTAX
                                ):

                                    # Cannot authenticate. Skip.

                                    logging.warn(
                                        "Cannot authenticate to directory "
                                        "server %s with dn %s. "
                                        "Skipping." % (
                                            url,
                                            directory_server.userdn
                                        )
                                    )

                                    continue

                                try:

                                    # Send the query

                                    result = conn.search_s(
                                        directory_server.base_dn,
                                        ldap.SCOPE_SUBTREE,
                                        query
                                    )

                                except ldap.SERVER_DOWN:

                                    # Cannot reach server. Skip.

                                    logging.warn("Cannot reach server %s. "
                                                 "Skipping." % url)

                                    continue

                                except (ldap.INVALID_CREDENTIALS,
                                        ldap.NO_SUCH_OBJECT):

                                    # Cannot authenticate or cannot query.
                                    # Perhaps the authentication was wrong (
                                    # guest login without an enabled guest
                                    # login)

                                    logging.warn("Cannot authenticate to "
                                                 "directory server %s as "
                                                 "guest or cannot query. "
                                                 "Skipping." % url)

                                    continue

                                if not result:

                                    if action.resolve_sender_fail:

                                        logging.warn(
                                            "Cannot resolve email %s. "
                                            "Skipping" % (
                                                self.mail_data["envelope_from"],
                                            )
                                        )

                                        return

                                    logging.info(
                                        "Cannot resolve email %s" % (
                                            self.mail_data["envelope_from"],
                                        )
                                    )

                                    continue

                                elif len(result) > 1:

                                    logging.warn(
                                        "Multiple results found for "
                                        "email %s. " %
                                        self.mail_data["envelope_from"]
                                    )

                                    if action.resolve_sender_fail:

                                        logging.warn(
                                            "Cannot reliable resolve email %s. "
                                            "Skipping" % (
                                                self.mail_data["envelope_from"],
                                            )
                                        )

                                        return

                                # Found something.

                                logging.debug("Found entry %s" % result[0][0])

                                # Store cache if we should

                                if directory_server.enable_cache:

                                    QueryCache.set(
                                        directory_server,
                                        query,
                                        result
                                    )

                                resolved_successfully = True

                                # Resolved successfully. Break this loop

                                break

                        if result is not None\
                           and len(result) == 1:

                            # Flatten result into replacement dict and
                            # convert to unicode strings while you're at it

                            for key in result[0][1].keys():

                                try:

                                    replacements["resolver"][
                                        key.lower()
                                    ] = unicode(
                                        ",".join(result[0][1][key]),
                                        "utf-8"
                                    )

                                except UnicodeDecodeError:

                                    # There's probably a binary string there.
                                    # Encode it in base64

                                    replacements["resolver"][
                                        key.lower()
                                    ] = unicode(
                                        base64.b64encode(
                                            "".join(result[0][1][key])
                                        )
                                    )

                    if not resolved_successfully and action.resolve_sender_fail:

                        # We didn't reach any directory server (url).

                        logging.warn(
                            "Cannot resolve email %s. "
                            "Skipping" % self.mail_data["envelope_from"]
                        )

                        return

                # Replace template text

                logging.debug("Replacing template text")

                # A template tag like {key}

                template = re.compile("\{([^}]*)\}")

                # A template tag referring to a dictionary like {key["test"]}

                subkey_template = re.compile("^([^\[]*)\[\"([^\"]*)\"\]$")

                while True:

                    # Search for template strings

                    match = template.search(disclaimer_text)

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

                            logging.warn("Cannot resolve key %s. "
                                         "Skipping" % key)

                            return

                        else:

                            logging.info("Cannot resolve key %s" % key)

                            value = ""

                    else:

                        if key in replacements:

                            value = replacements[key]

                        elif action.disclaimer.template_fail:

                            # We cannot resolve the key. Fail.

                            logging.warn("Cannot resolve key %s. "
                                         "Skipping" % key)

                            return

                        else:

                            logging.info("Cannot resolve key %s" % key)

                            value = ""

                    disclaimer_text = disclaimer_text.replace(
                        "{%s}" % replace_key,
                        value
                    )

            # If the HTML disclaimer should be the same as the text
            # disclaimer, reformat it to make it HTML-usable

            if content_type == "text/html" \
                    and action.disclaimer.html_use_text:

                disclaimer_text = self.make_html(disclaimer_text)

            # Carry out the action

            logging.debug(
                "Adding Disclaimer %s to body" % action.disclaimer.name
            )

            (encoding, new_text) = self.decode_mail(mail)

            # Convert to unicode string, if the mail's in utf-8

            if charset.lower() == "utf-8":

                new_text = unicode(new_text, "utf-8")

            if action.action == constants.ACTION_ACTION_REPLACETAG:

                new_text = re.sub(
                    action.action_parameters,
                    disclaimer_text,
                    new_text
                )

            elif action.action == constants.ACTION_ACTION_ADD:

                if content_type == "text/plain":

                    # text/plain can simply be concatenated

                    new_text = "%s\n%s" % (new_text, disclaimer_text)

                elif content_type == "text/html":

                    # text/html has to been put before the closing body-tag,
                    # so parse the text

                    html_part = etree.HTML(new_text)

                    disclaimer_part = etree.HTML(disclaimer_text)

                    if len(html_part.xpath("body")) > 0:

                        # Add the new part inside the existing body-tag

                        html_part.xpath("body")[0].append(
                            disclaimer_part.xpath("body")[0].getchildren()[0]
                        )

                    else:

                        # No body found. Just add the new part

                        html_part.append(
                            disclaimer_part.xpath("body")[0].getchildren()[0]
                        )

                    new_text = etree.tostring(
                        html_part,
                        pretty_print=True,
                        method="html"
                    )

            elif action.action == constants.ACTION_ACTION_ADDPART:

                # Add another mailpart by converting the current part to a
                # multipart, adding itself and the disclaimer part to it

                mail_disclaimer = None

                if content_type == "text/plain":

                    mail_disclaimer = email.mime.text.MIMEText(
                        disclaimer_text,
                        "plain",
                        disclaimer_charset
                    )

                elif content_type == "text/html":

                    mail_disclaimer = email.mime.text.MIMEText(
                        disclaimer_text,
                        "html",
                        disclaimer_charset
                    )

                new_mail = email.mime.multipart.MIMEMultipart("mixed")

                # Transfer the old headers to the new multipart mail

                bad_headers = (
                    "content-type",
                    "content-transfer-encoding",
                    "mime-version",
                    "content-disposition",
                    "content-description"
                )

                for header in mail.keys():

                    value = mail[header]

                    if header.lower() not in bad_headers:

                        new_mail.add_header(header, value)

                rfc822_part = email.mime.message.MIMEMessage(mail)

                new_mail.attach(rfc822_part)
                new_mail.attach(mail_disclaimer)

                # Use as_string once to let the boundary be generated

                new_mail.as_string()

                return new_mail

            else:

                logging.error("Invalid action value %d" % action.action)

                return

            # Convert from unicode string, if mail encoding is utf-8

            if charset.lower() == "utf-8":

                new_text = new_text.encode("utf-8")

            # Set payload to new text

            mail.set_payload(new_text)

            if "Content-Transfer-Encoding" in mail:

                # Remove original encode-transfer header

                del(mail["Content-Transfer-Encoding"])

            if encoding == "quoted-printable":

                email.encoders.encode_quopri(mail)

            elif encoding == "base64":

                email.encoders.encode_base64(mail)

            else:

                email.encoders.encode_7or8bit(mail)

            return mail
