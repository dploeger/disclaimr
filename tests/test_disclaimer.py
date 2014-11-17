""" Disclaimer testing """

from django.test import TestCase
from disclaimrwebadmin import models, constants
from disclaimr.configuration_helper import build_configuration
from disclaimr.milter_helper import MilterHelper


class DisclaimerTestCase(TestCase):

    """ Build up different disclaimer scenarios and check if they react right.
    """

    def setUp(self):

        """ A basic setup with a simple disclaimer, no directory servers, a basic rule and a basic action
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

        self.assertTrue(helper.enabled, "Helper wasn't enabled after initialization.")

        return helper

    def tool_run_real_test(self, header = None):

        """ Runs the test using the milter helper and returns the action dictionary of eob

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

        helper.body(self.test_text, {})
        return helper.eob({})

    def test_basic_add(self):

        """ The disclaimer will simply be added to the testmail. Check the returned body
        """

        returned = self.tool_run_real_test()

        self.assertEqual(returned[0]["repl_body"], "\n%s\n%s" % (self.test_text, self.disclaimer.text),
                         "Body was unexpectedly modified to %s" % returned[0]["repl_body"])

    def test_disabled_action(self):

        """ If we disable the only action, we should get an empty action dictionary back
        """

        self.action.enabled = False

        self.action.save()

        returned = self.tool_run_real_test()

        self.assertIsNone(returned, "We got an action dictionary back! %s" % returned)

    def test_basic_replace(self):

        """ Set the action to replace the disclaimer and not add it. Check the returned body
        """

        self.test_text = "Testmail #DISCLAIMER#"

        self.action.action = constants.ACTION_ACTION_REPLACETAG
        self.action.action_parameters = "#DISCLAIMER#"

        self.action.save()

        returned = self.tool_run_real_test()

        self.assertEqual(returned[0]["repl_body"], "\nTestmail %s" % self.disclaimer.text,
                         "Body was unexpectedly modified to %s" % returned[0]["repl_body"])

    def test_replacements_add(self):

        """ Test the replacement feature of sender, recipient and header replacement [add mode]
        """

        self.disclaimer.text = "{sender}|{recipient}|{header[\"Test\"]}"
        self.disclaimer.text_use_template = True

        self.disclaimer.save()

        returned = self.tool_run_real_test({"Test": "Test"})

        self.assertEqual(returned[0]["repl_body"], "\n%s\n%s|%s|Test" % (self.test_text, self.test_address, self.test_address),
                         "Body was unexpectedly modified to %s" % returned[0]["repl_body"])

    def test_replacements_replace(self):

        """ Test the replacement feature of sender, recipient and header replacement [add mode]
        """

        self.test_text = "Testmail #DISCLAIMER#"

        self.action.action = constants.ACTION_ACTION_REPLACETAG
        self.action.action_parameters = "#DISCLAIMER#"

        self.action.save()

        self.disclaimer.text = "{sender}|{recipient}|{header[\"Test\"]}"
        self.disclaimer.text_use_template = True

        self.disclaimer.save()

        returned = self.tool_run_real_test({"Test": "Test"})

        self.assertEqual(returned[0]["repl_body"], "\nTestmail %s|%s|Test" % (self.test_address, self.test_address),
                         "Body was unexpectedly modified to %s" % returned[0]["repl_body"])
