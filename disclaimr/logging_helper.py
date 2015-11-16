import logging
from logging.handlers import SysLogHandler

# the filter will take care of appending the
# queueid to log messages as soon as we have one
class queueFilter(logging.Filter):
    def __init__(self, id = ''):
        if len(id) > 0:
            id += ': '
        self.queue = id
    def filter(self, record):
        record.queueid = self.queue
        return True

# lets be nice and log our usual stuff like info and
# warn to syslogs LOG_MAIL facility instead of stdout    
syslog = logging.getLogger('disclaimr')
syslog.propagate = False # This will disable sending duplicates to stdout
syslog.addFilter(queueFilter())
logger = logging.StreamHandler()
handler = logging.handlers.SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_MAIL)
formatter = logging.Formatter('%(name)s[%(process)d]: %(queueid)s%(message)s')
handler.setFormatter(formatter)
syslog.addHandler(handler)