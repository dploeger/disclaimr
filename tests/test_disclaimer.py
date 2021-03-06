""" Disclaimer testing """
import email
from email.mime.application import MIMEApplication
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

    def tool_make_returned_mail(self, returned):

        headers = []

        for key in self.test_mail.keys():

            # Skip deleted headers

            if "delete_header" in returned and key in returned["delete_header"]:

                continue

            value = self.test_mail[key]

            # Change headers

            if "change_header" in returned and key in returned["change_header"]:

                value = returned["change_header"][key]

            headers.append("%s: %s" % (key, value))

        if "add_header" in returned:

            for key in returned["add_header"]:

                headers.append("%s: %s" % (key, returned["add_header"][key]))

        return email.message_from_string(
            "%s\n\n%s" % (
                "\n".join(headers),
                returned["repl_body"]
            )
        )

    def test_basic_add(self):

        """ The disclaimer will simply be added to the testmail.
            Check the returned body
        """

        returned = self.tool_run_real_test()

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s" % (self.test_text, self.disclaimer.text),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
        )

    def test_disabled_action(self):

        """ If we disable the only action, we should get an empty action
            dictionary back
        """

        self.action.enabled = False

        self.action.save()

        returned = self.tool_run_real_test()

        self.assertIsNone(
            returned,
            "We got an action dictionary back! %s" % returned
        )

    def test_disabled_secondaction(self):

        """ If we add an disabled action to a working set, it should just
            work fine.
        """

        action2 = models.Action()
        action2.rule = self.rule
        action2.position = 0
        action2.enabled = False
        action2.disclaimer = self.disclaimer

        action2.save()

        self.action.position = 1
        self.action.save()

        returned = self.tool_run_real_test()

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s" % (self.test_text, self.disclaimer.text),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
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
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "Testmail %s" % self.disclaimer.text,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1]
            )
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
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s|%s|Test" % (
                self.test_text,
                self.test_address,
                self.test_address
            ),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
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
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "Testmail %s|%s|Test" % (
                self.test_address,
                self.test_address
            ),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
        )

    def test_multiple_headers(self):

        """ Test a mail with multiple headers
        """

        returned = self.tool_run_real_test(header={
            "X-TEST1": "TEST",
            "X-TEST2": "TEST"
        })

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s" % (self.test_text, self.disclaimer.text),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
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

        returned_mail = self.tool_make_returned_mail(returned)

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[0]
            )[1],
            "%s\n%s" % (test_text, self.disclaimer.text),
            "Text-Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[0]
                )[1],
            )
        )

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[1]
            )[1],
            "<html><body>\n%s\n<p>%s</p>\n</body></html>\n" % (
                test_html,
                self.disclaimer.text
            ),
            "HTML-Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[1]
                )[1],
            )
        )

    def test_html(self):

        """ Test a HTML mail with an HTML disclaimer
        """

        test_html = "<p>TestHTML</p>"

        self.test_mail = MIMEText(test_html, "html", "UTF-8")

        returned = self.tool_run_real_test(make_mail=False)

        returned_mail = self.tool_make_returned_mail(returned)

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

        """ Test an unresolvable tag with template_fail=True inside a
            disclaimer, assuming that the mail isn't modified.
        """

        self.disclaimer.text = "{FAIL}"
        self.disclaimer.template_fail = True
        self.disclaimer.save()

        returned = self.tool_run_real_test()
        returned_mail = self.tool_make_returned_mail(returned)

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.test_mail
            )[1],
            milter_helper.MilterHelper.decode_mail(
                returned_mail
            )[1],
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail
                )[1],
            )
        )

    def test_unresolvable_tag_nofail(self):

        """ Test an unresolvable tag with template_fail=False inside a
            disclaimer, assuming that the mail is modified and the
            unresolvable tag is removed.
        """

        self.disclaimer.text = "{FAIL}"
        self.disclaimer.template_fail = False
        self.disclaimer.save()

        returned = self.tool_run_real_test()
        returned_mail = self.tool_make_returned_mail(returned)

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail
            )[1],
            "%s\n" % self.test_text,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail
                )[1],
            )
        )

    def test_unresolvable_subtag(self):

        """ Test an unresolvable subtag with template_fail=True
            inside a disclaimer assuming it will return an unmodified mail
        """

        self.disclaimer.text = "{FAIL[\"FAIL\"]}"
        self.disclaimer.template_fail = True
        self.disclaimer.save()

        returned = self.tool_run_real_test()
        returned_mail = self.tool_make_returned_mail(returned)

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.test_mail
            )[1],
            milter_helper.MilterHelper.decode_mail(
                returned_mail
            )[1],
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail
                )[1],
            )
        )

    def test_quoted_printable(self):

        """ Use a "quoted printable"-encoded mail as a test mail
        """

        self.test_mail = MIMEText(self.test_text, "plain", "iso-8859-1")

        returned = self.tool_run_real_test(make_mail=False)

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s" % (self.test_text, self.disclaimer.text),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
        )

    def test_html_disclaimer(self):

        """ Test a HTML (not "use text") disclaimer
        """

        self.disclaimer.html_use_text = False
        self.disclaimer.html = "<b>TEST-DISCLAIMER</b>"

        self.disclaimer.save()

        self.test_mail = MIMEText("<p>%s</p>" % self.test_text, "html")

        returned = self.tool_run_real_test(make_mail=False)

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "<html><body>\n<p>%s</p>\n%s\n</body></html>\n" % (
                self.test_text,
                self.disclaimer.html
            ),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
        )

    def test_multiple_rules(self):

        """ Add multiple rules assuming that only the first rule will be
        carried out.
        """

        rule2 = models.Rule()
        rule2.position = 1
        rule2.save()

        action2 = models.Action()

        action2.action = constants.ACTION_ACTION_ADD
        action2.disclaimer = self.disclaimer
        action2.rule = rule2
        action2.position = 0

        action2.save()

        requirement2 = models.Requirement()

        requirement2.rule = rule2
        requirement2.action = constants.REQ_ACTION_ACCEPT

        requirement2.save()

        returned = self.tool_run_real_test()

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s" % (self.test_text, self.disclaimer.text),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
        )

    def test_multiple_rules_continue(self):

        """ Use the continue flag for multiple rules assuming that all rules
        will be carried out.
        """

        rule2 = models.Rule()
        rule2.position = 1
        rule2.save()

        self.rule.continue_rules = True
        self.rule.save()

        disclaimer2 = models.Disclaimer()

        disclaimer2.name = "Test2"
        disclaimer2.text = "Test-Disclaimer2"

        disclaimer2.save()

        action2 = models.Action()

        action2.action = constants.ACTION_ACTION_ADD
        action2.disclaimer = disclaimer2
        action2.rule = rule2
        action2.position = 0

        action2.save()

        requirement2 = models.Requirement()

        requirement2.rule = rule2
        requirement2.action = constants.REQ_ACTION_ACCEPT

        requirement2.save()

        returned = self.tool_run_real_test()

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                self.tool_make_returned_mail(returned)
            )[1],
            "%s\n%s\nTest-Disclaimer2" % (self.test_text, self.disclaimer.text),
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    self.tool_make_returned_mail(returned)
                )[1],
            )
        )

    def test_disclaimer_add_part(self):

        """ Test an action, that adds a mime part with the disclaimer
        """

        self.action.action = constants.ACTION_ACTION_ADDPART

        self.action.save()

        returned = self.tool_run_real_test()

        returned_mail = self.tool_make_returned_mail(returned)

        # The first part shouldn't have been modified, but added as an
        # rfc-822 attachment

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[0].get_payload()[0]
            )[1],
            self.test_text,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[0]
                )[1],
            )
        )

        # The second part should be our disclaimer

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[1]
            )[1],
            self.disclaimer.text,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[1]
                )[1],
            )
        )

    def test_disclaimer_add_part_html(self):

        """ Test an action, that adds a mime part with a HTML disclaimer
        based on the text disclaimer
        """

        self.action.action = constants.ACTION_ACTION_ADDPART

        self.action.save()

        test_html = "<p>TestHTML</p>"

        self.test_mail = MIMEText(test_html, "html", "UTF-8")

        returned = self.tool_run_real_test(make_mail=False)

        returned_mail = self.tool_make_returned_mail(returned)

        # The first part shouldn't have been modified, but added as an
        # rfc-822 attachment

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[0].get_payload()[0]
            )[1],
            test_html,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[0]
                )[1],
            )
        )

        # The second part should be our disclaimer

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[1]
            )[1],
            self.disclaimer.text,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[1]
                )[1],
            )
        )

    def test_disclaimer_add_part_html_disclaimer(self):

        """ Test an action, that adds a mime part with a pure HTML disclaimer
        """

        self.action.action = constants.ACTION_ACTION_ADDPART

        self.action.save()

        test_html = "<p>TestHTML</p>"

        self.test_mail = MIMEText(test_html, "html", "UTF-8")

        self.disclaimer.html_use_text = False
        self.disclaimer.html = "<b>TEST-DISCLAIMER</b>"

        self.disclaimer.save()

        returned = self.tool_run_real_test(make_mail=False)

        returned_mail = self.tool_make_returned_mail(returned)

        # The first part shouldn't have been modified, but added as an
        # rfc-822 attachment

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[0].get_payload()[0]
            )[1],
            test_html,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[0]
                )[1],
            )
        )

        # The second part should be our disclaimer

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[1]
            )[1],
            self.disclaimer.html,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[1]
                )[1],
            )
        )

    def test_disclaimer_add_part_fallback(self):

        """ Test an action, that adds a mime part with the disclaimer,
        but uses a not-supported original mime-part (not text/plain or
        /html). This should give a text-disclaimer back.
        """

        self.action.action = constants.ACTION_ACTION_ADDPART

        self.action.save()

        self.disclaimer.html_use_text = False
        self.disclaimer.html = "<b>TEST-DISCLAIMER</b>"

        self.disclaimer.save()

        self.test_mail = MIMEApplication("TEST")

        returned = self.tool_run_real_test(make_mail=False)

        returned_mail = self.tool_make_returned_mail(returned)

        # The first part shouldn't have been modified, but added as an
        # rfc-822 attachment

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[0].get_payload()[0]
            )[1],
            "TEST",
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[0]
                )[1],
            )
        )

        # The second part should be the text-part of the disclaimer

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[1]
            )[1],
            self.disclaimer.text,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[1]
                )[1],
            )
        )

    def test_disclaimer_add_part_fallback_html(self):

        """ Test an action, that adds a mime part with the disclaimer,
        but uses a not-supported original mime-part (not text/plain or
        /html). Use the html fallback to generate a html-disclaimer.
        """

        self.action.action = constants.ACTION_ACTION_ADDPART

        self.action.save()

        self.disclaimer.html_use_text = False
        self.disclaimer.html = "<b>TEST-DISCLAIMER</b>"

        self.disclaimer.use_html_fallback = True

        self.disclaimer.save()

        self.test_mail = MIMEApplication("TEST")

        returned = self.tool_run_real_test(make_mail=False)

        returned_mail = self.tool_make_returned_mail(returned)

        # The first part shouldn't have been modified, but added as an
        # rfc-822 attachment

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[0].get_payload()[0]
            )[1],
            "TEST",
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[0]
                )[1],
            )
        )

        # The second part should be the text-part of the disclaimer

        self.assertEqual(
            milter_helper.MilterHelper.decode_mail(
                returned_mail.get_payload()[1]
            )[1],
            self.disclaimer.html,
            "Body was unexpectedly modified to %s" % (
                milter_helper.MilterHelper.decode_mail(
                    returned_mail.get_payload()[1]
                )[1],
            )
        )
