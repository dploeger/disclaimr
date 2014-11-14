""" Requirement testing """

from django.test import TestCase
from disclaimrwebadmin import models, constants
from disclaimr.configuration_helper import build_configuration
from disclaimr.milter_helper import MilterHelper


class RequirementsTestCase(TestCase):

    """ Build up different requirements and check if they react right.
    """

    def setUp(self):

        """ A basic setup with a simple disclaimer, no directory servers, a basic rule and a basic action
        """

        disclaimer = models.Disclaimer()

        disclaimer.name = "Test"
        disclaimer.text = "Test-Disclaimer"

        disclaimer.save()

        self.rule = models.Rule()
        self.rule.save()

        action = models.Action()

        action.action = constants.ACTION_ACTION_ADD
        action.disclaimer = disclaimer
        action.rule = self.rule
        action.position = 0

        action.save()

        pass

    def tool_basic_requirement(self):

        requirement = models.Requirement()

        requirement.rule = self.rule

        requirement.action = constants.REQ_ACTION_ACCEPT

        return requirement

    def tool_get_helper(self):

        configuration = build_configuration()

        helper = MilterHelper(configuration)

        # The requirement should basically be enabled

        self.assertTrue(helper.enabled, "Helper wasn't enabled after initialization.")

        return helper

    def test_wrong_ip(self):

        """ A requirement requiring a specific IP should work when connecting from the right ip and fail otherwise
        """

        requirement = self.tool_basic_requirement()

        requirement.sender_ip = "1.1.1.1"
        requirement.sender_ip_cidr = "32"

        requirement.save()

        helper = self.tool_get_helper()

        # Try to mimic a connection from the right IP

        helper.connect("", "", "1.1.1.1", "", {})

        self.assertTrue(helper.enabled, "Helper wasn't enabled after connecting with the right IP")

        # Try to mimic a connection from the wrong IP

        helper = self.tool_get_helper()

        helper.connect("", "", "1.1.1.2", "", {})

        self.assertFalse(helper.enabled, "Helper was enabled after connecting with the wrong IP")

    def test_wrong_sender(self):

        """ A requirement requiring a specific sender should work when using it and fail otherwise
        """

        requirement = self.tool_basic_requirement()

        requirement.sender = "abc"

        requirement.save()

        helper = self.tool_get_helper()

        # Try to mimic a valid sender

        helper.connect("", "", "1.1.1.1", "", {})
        helper.mail_from("abc", {})

        self.assertTrue(helper.enabled, "Helper wasn't enabled after sending to the right sender")

        helper = self.tool_get_helper()

        helper.connect("", "", "1.1.1.1", "", {})
        helper.mail_from("def", {})

        self.assertFalse(helper.enabled, "Helper was enabled after sending to the wrong sender")


    def test_wrong_recipient(self):

        """ A requirement requiring a specific recipient should work when using it and fail otherwise
        """

        requirement = self.tool_basic_requirement()

        requirement.recipient = "abc"

        requirement.save()

        helper = self.tool_get_helper()

        # Try to mimic a valid recipient

        helper.connect("", "", "1.1.1.1", "", {})
        helper.rcpt("abc", {})

        self.assertTrue(helper.enabled, "Helper wasn't enabled after sending to the right recipient")

        helper = self.tool_get_helper()

        helper.connect("", "", "1.1.1.1", "", {})
        helper.rcpt("def", {})

        self.assertFalse(helper.enabled, "Helper was enabled after sending to the wrong recipient")