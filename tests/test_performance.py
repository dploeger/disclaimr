""" Performance testing """
import datetime
import smtplib
from unittest import SkipTest
from django.conf import settings
from django.test import TestCase


class PerformanceTest(TestCase):

    """ Send multiple messages and check the needed time
    """

    def setUp(self):

        if not settings.TEST_PERFORMANCE_ENABLE:

            raise SkipTest()

    def test_performance(self):

        """ Send a lot of mails and check the needed time to process.
        """

        test_start = datetime.datetime.now()

        server = smtplib.SMTP(settings.TEST_PERFORMANCE["smtp_server"])

        if not settings.TEST_PERFORMANCE["username"] == "":

            server.login(settings.TEST_PERFORMANCE["username"], settings.TEST_PERFORMANCE["password"])

        for i in range(settings.TEST_PERFORMANCE["sends"]):

            server.sendmail(
                settings.TEST_PERFORMANCE["sender"],
                settings.TEST_PERFORMANCE["recipient"],
                settings.TEST_PERFORMANCE["message"]
            )

        server.close()

        test_end = datetime.datetime.now()

        time_taken = test_end-test_start

        self.assertLessEqual(
            time_taken.total_seconds(),
            settings.TEST_PERFORMANCE["timeout"],
            "Test took too long: %s seconds" % time_taken.total_seconds()
        )
