""" disclaimr - Mail disclaimer server """
__version__ = 'v1.0-rc2'

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
from disclaimr.logging_helper import queueFilter

syslog = logging.getLogger('disclaimr-milter')

try:
    import systemd.daemon
    HAS_SYSTEMD_PYTHON = True
except ImportError:
    syslog.warning("Missing module systemd.daemon, "
                   "systemd support not available! "
                   "Please install systemd-python")
    HAS_SYSTEMD_PYTHON = False

class DisclaimrMilter(lm.ForkMixin, lm.MilterProtocol):

    """ Disclaimr Milter

    This is the main milter thread for disclaimr based on
    libmilter.MiterProtocol. It will be given the options and a basic
    configuration set. During its workflow, it will narrow down the available
    requirements and disable itself, once no requirements are left, so
    that no unneccesary steps are taken.

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

        if self.helper.rcptmatch:
            logging.debug("We already have a positive recipient match "
                          "so we skip all further checks.")
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

        syslog.addFilter(queueFilter(cmd_dict["i"]))

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

        for task_item in tasks.keys():

            if task_item == "repl_body":

                # Change body

                self.replBody(tasks[task_item])

            elif task_item == "add_header":

                # Add header

                for header in tasks["add_header"].keys():

                    self.addHeader(header, tasks["add_header"][header])

            elif task_item == "change_header":

                # Change header

                for header in tasks["change_header"].keys():

                    self.chgHeader(header, tasks["change_header"][header])

            elif task_item == "delete_header":

                # Remove header

                for header in tasks["delete_header"]:

                    self.chgHeader(header, "")

        return lm.CONTINUE

    def close(self):

        """ Called, when a connection with a client is closed
        """

        logging.debug("Close called. QID: %s" % self._qid)

        # If we still have a queue id on disconnect
        # something went fu will processing the mail
        if self._qid:
            syslog.critical("Mail processing failed -> Check journalctl " \
                            "and if you found a bug make sure too report it " \
                            "at https://github.com/dploeger/disclaimr")

        else:
            syslog.info("Done")

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

                syslog.warn(emsg)
                p.transport = None
                sock.close()


def run_disclaimr_milter():

    """ Start the multiforking milter daemon
    """

    # Set milter options
    opts = \
        lm.SMFIF_CHGBODY | \
        lm.SMFIF_ADDHDRS | \
        lm.SMFIF_CHGHDRS

    # Initialize Fork Factory
    f = lm.ForkFactory(options.socket, DisclaimrMilter, opts)

    # Check for systemd support and, if started by systemd,
    # report that we are ready to accpet connections
    logging.debug("HAS_SYSTEMD_PYTHON: %s" % HAS_SYSTEMD_PYTHON)
    if HAS_SYSTEMD_PYTHON and systemd.daemon.booted():
        logging.debug("Milter started by systemd and ready...")
        systemd.daemon.notify('READY=1')

    # Register signal handler for killing

    def signal_handler(num, frame):
        syslog.info("Stopping disclaimr " +
                    __version__ +
                    " listening on " +
                    options.socket)
        
        f.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler) # needed to terminate the process through systemd

    # Run

    try:
        f.run()

    except KeyboardInterrupt:
        
        # CTRL-C should be handeled like this
        # since SIGINT will call it anyway
        
        logging.debug("Got CTRL-C...")

    except Exception, e:

        # Exception occured. Stop everything and show it.

        f.close()

        print >> sys.stderr, 'EXCEPTION OCCURED: %s' % e

        traceback.print_tb(sys.exc_traceback)

        sys.exit(3)

if __name__ == '__main__':

    # Argument handling

    parser = argparse.ArgumentParser(
        description="Disclaimr - Mail disclaimer server. Starts a "
                    "milter daemon, that adds dynamic disclaimers to messages"
    )

    parser.add_argument(
        "-s",
        "--socket",
        dest="socket",
        default="inet:127.0.0.1:5000",
        help="Socket to open. IP-Sockets need to be in the form "
             "inet:<ip>:<port> [inet:127.0.0.1:5000]"
    )

    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Be quiet doing things"
    )

    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "-i",
        "--ignore-cert",
        dest="ignore_cert",
        action="store_true",
        help="Ignore certificates when connecting to "
             "tls-enabled directory servers"
    )

    parser.add_argument(
        "-c",
        "--clean-cache",
        dest="clean_cache",
        metavar="CYCLES",
        help="Clean query cache (remove timed out items) every CYCLES [20000]",
        default=20000
    )

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

    syslog.info("Starting disclaimr " +
                __version__ +
                " listening on "
                + options.socket)

    if options.ignore_cert:

        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    # Fetch basic configuration data for efficiency

    logging.debug("Generating basic configuration")

    configuration = build_configuration()

    # Run Disclaimr

    run_disclaimr_milter()