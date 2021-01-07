# Logging the way we like it.

import logging
from logging.handlers import RotatingFileHandler

"""
This module generates log files that have a max length of 50K bytes.
It uses RotatingFileHandler and creates no more than 3 backup files;
that means that when the file reaches 50K bytes, it is renamed and
a new logfile is opened.
Exampe: you name the file "myapp.log". Backup files will be named:
myapp.log.1, myapp.log.2, myapp.log.3. You can change the number of backups
by editing this code.

Explanation of logger levels.
Specify level=logging.CRITICAL, etc.
Each level includes messages from the levels before it. So specifying WARNING will also
output CRITICAL and ERROR messages to the logfile.
DEBUG is most wordy and should be turned off in production runs.
Print to log file using logger.info('message') or logger.debug or logger.warning, etc.
When level=logging.INFO, any time the code runs logger.debug, you will not get that message.
"""

defFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')
def setup_logger(name, log_file, formatter=defFormatter, level=logging.INFO):
    """
    Setup as many loggers as you want
    :param name: typically the module name. You should use __name__ unless you have a better idea.
    :param log_file: name of the logging file.
    :param formatter: defines the format for each log line.
    :param level: standard logger levels are CRITICAL, ERROR, WARNING, INFO, DEBUG.
    :return: the logger. Use it like this: logger.info('message')
    """
    handler = RotatingFileHandler(log_file, maxBytes=50000, backupCount=3)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger
