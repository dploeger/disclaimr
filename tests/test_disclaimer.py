""" Disclaimer testing """
import base64
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.test import TestCase
from disclaimr import milter_helper
from disclaimrwebadmin import models, constants
from disclaimr.configuration_helper import build_configuration
from disclaimr.milter_helper import MilterHelper


class DisclaimerTestCase(TestCase):

    """ Build up different disclaimer scenarios and check if they react right.
    """

    def setUp(self):

        """ A basic setup with a simple disclaimer, no directory servers,
            a basic rule and a basic action
        """

        self.test_text = "Testmail"
        self.test_address = "test@company.com"

        self.disclaimer = models.Disclaimer()

        self.disclaimer.name = "Test"
        self.disclaimer.text = "Test-Disclaimer"

        self.disclaimer.save()

        self.rule = models.Rule()
        self.rule.save()

        self.action = models.Action()

        self.action.action = constants.ACTION_ACTION_ADD
        self.action.disclaimer = self.disclaimer
        self.action.rule = self.rule
        self.action.position = 0

        self.action.save()

        requirement = models.Requirement()

        requirement.rule = self.rule
        requirement.action = constants.REQ_ACTION_ACCEPT

        requirement.save()

    def tool_get_helper(self):

        """ Return a configured milter helper

        :return: A Milter helper
        """

        configuration = build_configuration()

        helper = MilterHelper(configuration)

        # The requirement should basically be enabled

        self.assertTrue(
            helper.enabled,
            "Helper wasn't enabled after initialization."
        )

        return helper

    def tool_add_bodies(self, helper, mail):

        if mail.is_multipart():

            for payload in mail.get_payload():

                self.tool_add_bodies(helper, payload)

        else:

            helper.body(mail.as_string(), {})

    def tool_run_real_test(self, header=None, make_mail=True):

        """ Runs the test using the milter helper and returns the
            action dictionary of eob

        :return: the action dictionary of eob()
        """

        helper = self.tool_get_helper()

        helper.connect("", "", "1.1.1.1", "", {})
        helper.mail_from(self.test_address, {})
        helper.rcpt(self.test_address, {})

        if header is not None:

            for key in header.iterkeys():

                helper.header(key, header[key], {})

            helper.eoh({})

        else:

            # Add at least one header for proper mail processing

            helper.header("From", "nobody", {})
            helper.eoh({})

        if make_mail:

            self.test_mail = MIMEText(self.test_text, "plain", "UTF-8")

        helper.body(self.test_mail.as_string(), {})

        return helper.eob({})

    def test_basic_add(self):

        """ The disclaimer will simply be added to the testmail.
            Check the returned body
        """

        returned = self.tool_run_real_test()

        self.assertEqual(
            returned[0]["repl_body"],
            base64.b64encode(
                "%s\n%s" % (self.test_text, self.disclaimer.text)
            ),
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_disabled_action(self):

        """ If we disable the only action, we should get an empty action
            dictionary back

        FIXME Coverage problem
        """

        self.action.enabled = False

        self.action.save()

        returned = self.tool_run_real_test()

        self.assertIsNone(
            returned,
            "We got an action dictionary back! %s" % returned
        )

    def test_basic_replace(self):

        """ Set the action to replace the disclaimer and not add it. Check the
            returned body
        """

        self.test_text = "Testmail #DISCLAIMER#"

        self.action.action = constants.ACTION_ACTION_REPLACETAG
        self.action.action_parameters = "#DISCLAIMER#"

        self.action.save()

        returned = self.tool_run_real_test()

        self.assertEqual(
            returned[0]["repl_body"],
            base64.b64encode("Testmail %s" % self.disclaimer.text),
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_replacements_add(self):

        """ Test the replacement feature of sender, recipient and header
            replacement [add mode]
        """

        self.disclaimer.text = "{sender}|{recipient}|{header[\"Test\"]}"
        self.disclaimer.text_use_template = True

        self.disclaimer.save()

        returned = self.tool_run_real_test({"Test": "Test"})

        self.assertEqual(
            returned[0]["repl_body"],
            base64.b64encode("%s\n%s|%s|Test" % (
                self.test_text,
                self.test_address,
                self.test_address
            )),
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_replacements_replace(self):

        """ Test the replacement feature of sender, recipient and header
            replacement [add mode]
        """

        self.test_text = "Testmail #DISCLAIMER#"

        self.action.action = constants.ACTION_ACTION_REPLACETAG
        self.action.action_parameters = "#DISCLAIMER#"

        self.action.save()

        self.disclaimer.text = "{sender}|{recipient}|{header[\"Test\"]}"
        self.disclaimer.text_use_template = True

        self.disclaimer.save()

        returned = self.tool_run_real_test({"Test": "Test"})

        self.assertEqual(
            returned[0]["repl_body"],
            base64.b64encode(
                "Testmail %s|%s|Test" % (self.test_address, self.test_address)
            ),
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_multiple_headers(self):

        """ Test a mail with multiple headers
        """

        returned = self.tool_run_real_test(header={
            "X-TEST1": "TEST",
            "X-TEST2": "TEST"
        })

        self.assertEqual(
            returned[0]["repl_body"],
            base64.b64encode("%s\n%s" % (self.test_text, self.disclaimer.text)),
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_multipart(self):

        """ Test a multipart mail
        """

        test_text = "TestPlain"
        test_html = "<p>TestHTML</p>"

        text_part = MIMEText(test_text, "plain", "UTF-8")
        html_part = MIMEText(test_html, "html", "UTF-8")

        self.test_mail = MIMEMultipart("alternative")
        self.test_mail.attach(text_part)
        self.test_mail.attach(html_part)

        returned = self.tool_run_real_test(make_mail=False)

        returned_mail = email.message_from_string(
            "From: nobody\nMIME-Version: 1.0\nContent-Type: %s\n\n%s" % (
                self.test_mail["Content-Type"],
                returned[0]["repl_body"]
            )
        )

        self.assertEqual(
            returned_mail.get_payload()[0].get_payload(),
            email.encoders._bencode("%s\n%s" % (test_text, self.disclaimer.text)),
            "Text-Body was unexpectedly modified to %s" % (
                base64.b64decode(returned_mail.get_payload()[0].get_payload()),
            )
        )

        self.assertEqual(
            returned_mail.get_payload()[1].get_payload(),
            email.encoders._bencode(
                "<html><body>\n%s\n<p>%s</p>\n</body></html>\n" % (
                    test_html,
                    self.disclaimer.text
                )
            ),
            "HTML-Body was unexpectedly modified to %s" % (
                base64.b64decode(returned_mail.get_payload()[1].get_payload()),
            )
        )

    def test_html(self):

        """ Test a HTML mail with an HTML disclaimer
        """

        test_html = "<p>TestHTML</p>"

        self.test_mail = MIMEText(test_html, "html", "UTF-8")

        returned = self.tool_run_real_test(make_mail=False)

        headers = []

        for key in self.test_mail.keys():

            headers.append("%s: %s" % (key, self.test_mail[key]))

        returned_mail = email.message_from_string(
            "%s\n\n%s" % (
                "\n".join(headers),
                returned[0]["repl_body"]
            )
        )

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail
            )[1],
            "<html><body>\n%s\n<p>%s</p>\n</body></html>\n" % (
                test_html,
                self.disclaimer.text
            ),
            "HTML-Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail
                )[1]
            )
        )

    def test_unresolvable_tag(self):

        """ Test an unresolvable tag with template_fail=True inside a disclaimer
        """

        # TODO

        raise NotImplementedError

    def test_unresolvable_subtag(self):

        """ Test an unresolvable subtag with template_fail=True
            inside a disclaimer
        """

        # TODO

        raise NotImplementedError

    def test_charset(self):

        """ Test a mail with a non-utf8-charset
        """

        # TODO

        raise NotImplementedError
