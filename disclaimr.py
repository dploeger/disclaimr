""" disclaimr - Mail disclaimer server
"""
import argparse
import socket
import ldap
import os

import libmilter as lm
import signal
import traceback
import sys
import logging

# Setup Django
from disclaimr.query_cache import QueryCache

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "disclaimrweb.settings")
import django
django.setup()

from disclaimr.configuration_helper import build_configuration
from disclaimr.milter_helper import MilterHelper


class DisclaimrMilter(lm.ForkMixin, lm.MilterProtocol):

    """ Disclaimr Milter

    This is the main milter thread for disclaimr based on libmilter.MiterProtocol. It will be given the options and a basic
    configuration set. During its workflow, it will narrow down the available requirements and disable itself,
    once no requirements are left, so that no unneccesary steps are taken.

    Uses the MilterHelper to do the real work

    """

    def __init__(self, opts=0, protos=0):

        """ Initialize the milter

        :param opts: SMFIF-options for this milter
        :param protos: SMFIP-options for this milter
        :return: The milter
        """

        lm.MilterProtocol.__init__(self, opts, protos)
        lm.ForkMixin.__init__(self)

        self.helper = MilterHelper(configuration)

        logging.debug("Initialising Milter Fork")

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

        self.helper.connect(hostname, family, ip, port, cmd_dict)

        return lm.CONTINUE

    @lm.noReply
    def mailFrom(self, addr, cmd_dict):

        """ Called when the MAIL FROM-envelope has been sent

        :param addr: The MAIL FROM-envelope value
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.helper.enabled:

            return lm.CONTINUE

        logging.debug("MAILFROM: %s" % addr)

        self.helper.mail_from(addr, cmd_dict)

        return lm.CONTINUE

    @lm.noReply
    def rcpt(self, recip, cmd_dict):

        """ Called when the RCPT TO-envelope has been set

        :param recip: The RCPT TO-envelope
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.helper.enabled:

            return lm.CONTINUE

        logging.debug("RCPT: %s" % recip)

        self.helper.rcpt(recip, cmd_dict)

        return lm.CONTINUE

    @lm.noReply
    def header(self, key, val, cmd_dict):

        """ Called when a header is received

        :param key: The header key
        :param val: The header value
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.helper.enabled:

            return lm.CONTINUE

        logging.debug("HEADER: %s: %s" % (key, val))

        self.helper.header(key, val, cmd_dict)

        return lm.CONTINUE

    @lm.noReply
    def eoh(self, cmd_dict):

        """ Called, when all headers were sent

        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.helper.enabled:

            return lm.CONTINUE

        self.helper.eoh(cmd_dict)

        return lm.CONTINUE

    @lm.noReply
    def body(self, chunk, cmd_dict):

        """ Called when a body chunk has been received

        :param chunk: A chunk of the body
        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.helper.enabled:

            return lm.CONTINUE

        logging.debug("BODY: (chunk) %s" % chunk)

        self.helper.body(chunk, cmd_dict)

        return lm.CONTINUE

    def eob(self, cmd_dict):

        """ Called when all body chunks have been received

        :param cmd_dict: A libmilter command dictionary
        :return: A libmilter action
        """

        if not self.helper.enabled:

            return lm.CONTINUE

        logging.debug("ENDOFBODY: Processing actions...")

        tasks = self.helper.eob(cmd_dict)

        for task in tasks:

            for task_item in task.iterkeys():

                if task_item == "repl_body":

                    self.replBody(task[task_item])

        return lm.CONTINUE

    def close(self):

        """ Called, when a connection with a client is closed
        """

        logging.debug("Close called. QID: %s" % self._qid)


class DisclaimrForkFactory(lm.ForkFactory):

    def run(self):

        self._setupSock()

        cycle_timer = 0

        while True:

            cycle_timer += 1

            if cycle_timer > options.clean_cache:

                # We have to clear the cache

                logging.debug("Flushing cache.")

                cycle_timer = 0
                QueryCache.flush()

            if self._close.isSet():
                break

            try:

                sock, addr = self.sock.accept()

            except socket.timeout:

                logging.debug("Accept socket timed out")
                continue

            except socket.error, e:

                emsg = 'ERROR IN ACCEPT(): %s' % e
                self.log(emsg)
                logging.debug(emsg)
                continue

            sock.settimeout(self.cSockTimeout)
            p = self.protocol(self.opts)
            p.transport = sock

            try:

                p.start()

            except Exception, e:

                emsg = 'An error occured starting the thread for ' + \
                       'connect from: %r: %s' % (addr, e)

                logging.warn(emsg)
                p.transport = None
                sock.close()


def run_disclaimr_milter():

    """ Start the multiforking milter daemon
    """

    # Set milter options
    opts = lm.SMFIF_CHGBODY | lm.SMFIF_CHGFROM | lm.SMFIF_ADDRCPT | lm.SMFIF_QUARANTINE

    # Initialize Fork Factory
    f = lm.ForkFactory(options.socket, DisclaimrMilter, opts)

    # Register signal handler for killing

    def signal_handler(num, frame):
        f.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Run

    try:
        f.run()

    except Exception, e:

        # Exception occured. Stop everything and show it.

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

    parser.add_argument("-c", "--clean-cache", dest="clean_cache", metavar="CYCLES", help="Clean query cache (remove timed out "
                                                                                          "items) every CYCLES")

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

    configuration = build_configuration()

    # Run Disclaimr

    run_disclaimr_milter()