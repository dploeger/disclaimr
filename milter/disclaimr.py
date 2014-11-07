""" disclaimr - Mail disclaimer server
"""
import argparse
import os

import libmilter as lm
import signal
import traceback
import sys
from string import Template
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "disclaimrweb.disclaimrweb.settings")

from disclaimrweb.disclaimrwebadmin import models


class DisclaimrMilter(lm.ForkMixin, lm.MilterProtocol):

    def __init__(self, opt):

        lm.MilterProtocol.__init__(self)
        lm.ForkMixin.__init__(self)

        self.mail_data = {
            "headers": {},
            "body": ""
        }

        self.options = opt

    @lm.noReply
    def connect(self, hostname, family, ip, port, cmd_dict):

        self.mail_data["sender_ip"] = ip
        return lm.CONTINUE

    @lm.noReply
    def mailFrom(self, addr, cmd_dict):

        self.mail_data["envelope_from"] = addr
        return lm.CONTINUE

    @lm.noReply
    def rcpt(self, recip, cmd_dict):

        self.mail_data["envelope_rcpt"] = recip
        return lm.CONTINUE

    @lm.noReply
    def header(self, key, val, cmd_dict):

        self.mail_data["headers"][key] = val

        return lm.CONTINUE


    @lm.noReply
    def body(self, chunk, cmd_dict):

        self.mail_data["body"] += chunk
        return lm.CONTINUE

    def eob(self, cmd_dict):

        # Change Disclaimer according to database

        return lm.CONTINUE

    def close(self):
        self.log('Close called. QID: %s' % self._qid)


def run_disclaimr_milter():

    # We can set our milter opts here
    opts = lm.SMFIF_CHGBODY | lm.SMFIF_CHGFROM | lm.SMFIF_ADDRCPT | lm.SMFIF_QUARANTINE

    # We initialize the factory we want to use (you can choose from an
    # AsyncFactory, ForkFactory or ThreadFactory.  You must use the
    # appropriate mixin classes for your milter for Thread and Fork)
    f = lm.ForkFactory('inet:127.0.0.1:5000' , DisclaimrMilter , opts)

    def signal_handler(num , frame):
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

    # Run Disclaimr

    #run_disclaimr_milter(options)
