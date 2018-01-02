#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import SSHLogger
import multiprocessing as mp
import logging
import time
import os

config_file = os.path.abspath('logger.conf')
# because OSX adds /var -> /private/var
if config_file.startswith('/private'):
    config_file = config_file[8:]


def main(port=None):
    # logging_config = config.get('LOGGING')
    sshlogger = SSHLogger('example', logging_level=logging.DEBUG,
                          console=True, consolidate=False, port=port,
                          logdir='/tmp')
    logger = sshlogger.start()

    logger.info("Logger host, port: {}, {}"
                .format(sshlogger.host, sshlogger.port))

    while True:
        time.sleep(0.5)

    sshlogger.stop()


def cmdargs():
    import argparse

    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]

    parser = argparse.ArgumentParser(
        description="{} runs SSH logging client example".format(progname))
    parser.add_argument('-p', '--port', type=int, required=True,
                        help="""Port for logging server.""")
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    args = cmdargs()
    main(**vars(args))
