""" disclaimr - Mail disclaimer server
"""

import libmilter as lm
import signal, traceback
import sys
from string import Template
import logging


class DisclaimrMilter(lm.ForkMixin, lm.MilterProtocol):

    def __init__(self, opts=0, protos=0):

        lm.MilterProtocol.__init__(self, opts, protos)
        lm.ForkMixin.__init__(self)

        self.mail_data = {
            "headers": {},
            "body": ""
        }

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

    # Setup logging

    # Run Disclaimr

    run_disclaimr_milter()