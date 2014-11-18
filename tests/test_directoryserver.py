""" Directory server testing """
from unittest import SkipTest
from django.conf import settings

from django.test import TestCase
import ldap
import time
from disclaimr.query_cache import QueryCache
from disclaimrwebadmin import models, constants
from disclaimr.configuration_helper import build_configuration
from disclaimr.milter_helper import MilterHelper


class DirectoryServerTestCase(TestCase):

    """ Build up different a resolution testsuite to test the directory server
        resolution feature
    """

    def setUp(self):

        """ A basic setup with a simple disclaimer, no directory servers, a
            basic rule and a basic action
        """

        if not settings.TEST_DIRECTORY_SERVER_ENABLE:

            # Skip this test, if it isn't enabled

            raise SkipTest()

        self.test_text = "Testmail"

        # Build Disclaimer

        disclaimer = models.Disclaimer()

        disclaimer.name = "Test"
        disclaimer.text = "{resolver[\"%s\"]}" % \
                          settings.TEST_DIRECTORY_SERVER["field"]

        disclaimer.save()

        # Build rule

        self.rule = models.Rule()
        self.rule.save()

        # Build requirement

        requirement = models.Requirement()

        requirement.rule = self.rule
        requirement.action = constants.REQ_ACTION_ACCEPT

        requirement.save()

        # Build directory server

        self.directory_server = models.DirectoryServer()

        self.directory_server.name = "Test"
        self.directory_server.enabled = True
        self.directory_server.enable_cache = False
        self.directory_server.base_dn = \
            settings.TEST_DIRECTORY_SERVER["base_dn"]
        self.directory_server.search_query = \
            settings.TEST_DIRECTORY_SERVER["query"]

        if settings.TEST_DIRECTORY_SERVER["user_dn"] == "":

            self.directory_server.auth = constants.DIR_AUTH_NONE

        else:

            self.directory_server.auth = constants.DIR_AUTH_SIMPLE
            self.directory_server.userdn = \
                settings.TEST_DIRECTORY_SERVER["user_dn"]
            self.directory_server.password = \
                settings.TEST_DIRECTORY_SERVER["password"]

        self.directory_server.save()

        directory_server_url = models.DirectoryServerURL()

        directory_server_url.directory_server = self.directory_server
        directory_server_url.url = settings.TEST_DIRECTORY_SERVER["url"]
        directory_server_url.position = 0

        directory_server_url.save()

        # Build action

        action = models.Action()

        action.action = constants.ACTION_ACTION_ADD
        action.disclaimer = disclaimer
        action.rule = self.rule
        action.position = 0
        action.resolve_sender = True

        action.save()

        action.directory_servers = [self.directory_server]

        action.save()

        # We will not check against certificates here

        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

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

    def tool_run_real_test(self, address=None):

        """ Runs the test using the milter helper and returns the action
            dictionary of eob

        :return: the action dictionary of eob()
        """

        if address is None:

            address = settings.TEST_DIRECTORY_SERVER["address"]

        helper = self.tool_get_helper()

        helper.connect("", "", "1.1.1.1", "", {})
        helper.mail_from(address, {})
        helper.rcpt(address, {})
        helper.body(self.test_text, {})
        return helper.eob({})

    def test_disabled_directoryserver(self):

        """ If we disable the directory server (and set the resolution to
            not fail, which is the default), we should get the
            text of our email plus a newline resulting of the addition of the
            (empty) disclaimer back.
        """

        self.directory_server.enabled = False

        self.directory_server.save()

        returned = self.tool_run_real_test()

        self.assertEqual(
            returned[0]["repl_body"],
            "\n%s\n" % self.test_text,
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_replacement(self):

        """ Try to resolve the sender and test the resulting replacement.
        """

        returned = self.tool_run_real_test()

        self.assertEqual(
            returned[0]["repl_body"],
            "\n%s\n%s" % (
                self.test_text,
                settings.TEST_DIRECTORY_SERVER["value"]
            ),
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_replacement_fail(self):

        """ If we cannot resolve the sender and set resolution to fail,
            we should get an unmodified mail back.
        FIXME coverage issue
        """

        action = models.Action.objects.filter(rule__id=self.rule.id)[0]
        action.resolve_sender_fail = True
        action.save()

        # Run the real test with a modified, possibly failing address

        returned = self.tool_run_real_test(
            address="%s|FAILED|" % settings.TEST_DIRECTORY_SERVER["address"]
        )

        self.assertEqual(
            returned[0]["repl_body"],
            "\n%s" % self.test_text,
            "Body was unexpectedly modified to %s" % returned[0]["repl_body"]
        )

    def test_caching(self):

        """ Test the query cache feature by checking, if a query was cached
        """

        self.directory_server.enable_cache = True
        self.directory_server.save()

        # Run the real test and check, if the query was cached

        self.tool_run_real_test()

        self.assertIn(
            self.directory_server.id,
            QueryCache.cache,
            "Directory server wasn't cached at all!"
        )

        self.assertGreater(
            len(QueryCache.cache[self.directory_server.id]),
            1,
            "Item seemingly wasn't cached."
        )

        # Clean the cache for other tests

        QueryCache.cache = {}

    def test_caching_timeout(self):

        """ Test the query cache timeout by mimicing the use
        """

        self.directory_server.enable_cache = True
        self.directory_server.cache_timeout = 1
        self.directory_server.save()

        QueryCache.set(self.directory_server, "TEST", "TEST")

        self.assertIsNotNone(
            QueryCache.get(self.directory_server, "TEST"),
            "Cached item wasn't returned."
        )

        # Sleep for the cache to time out

        time.sleep(self.directory_server.cache_timeout + 1)

        self.assertIsNone(
            QueryCache.get(self.directory_server, "TEST"),
            "Cached item didn't time out."
        )

        # Clean the cache for other tests

        QueryCache.cache = {}

    def test_caching_flush(self):

        """ Test the query cache flushing method
        """

        self.directory_server.enable_cache = True
        self.directory_server.cache_timeout = 1
        self.directory_server.save()

        QueryCache.set(self.directory_server, "TEST", "TEST")

        self.assertIsNotNone(
            QueryCache.get(self.directory_server, "TEST"),
            "Cached item wasn't returned."
        )

        # Sleep for the cache to time out

        time.sleep(self.directory_server.cache_timeout + 1)

        QueryCache.flush()

        # The cache should be empty now

        self.assertEqual(len(QueryCache.cache), 0, "The cache wasn't flushed.")

        # Clean the cache for other tests

        QueryCache.cache = {}

    def test_unreachable(self):

        """ Test an unreachable directory server
        TODO
        """

        pass

    def test_invalid_auth(self):

        """ Test invalid username/passwort for a directory server
        TODO
        """

        pass

    def test_unreachable_guest(self):

        """ Test an unreachable directory server without simple auth
        TODO
        """

        pass

    def test_invalid_auth_guest(self):

        """ Test invalid username/passwort for a directory server without
        simple auth. Disabling simple auth on the directory
        server when connecting to a simple-auth-requiring ldap server should be
        a sufficient test.
        TODO
        """

        pass

    def test_unresolvable(self):

        """ Test for an unresolvable address in the directory server
        TODO
        """

        pass

    def test_multiple(self):

        """ Test for multiple resolved addresses
        TODO
        """

        pass