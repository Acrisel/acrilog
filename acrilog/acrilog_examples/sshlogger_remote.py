#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import SSHLoggerClientHandler
import multiprocessing as mp
import logging
import os
import time

module_logger = logging.getLogger(__name__)
module_logger.addHandler(logging.StreamHandler())
module_logger.setLevel(logging.DEBUG)


def main(port):
    print('running')

    logger_info = {
        'name': 'example.e1',
        'port': port,
        'logging_level': logging.DEBUG,
        # 'server_host': 'arnon-mbp',
        }

    logger = logging.getLogger('example.e1')
    handler = SSHLoggerClientHandler(
        logger_info=logger_info, ssh_host='arnon-mbp-acris', verbose=False)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    print('sleeping for a little.')
    time.sleep(5)
    print('done sleeping.')

    logger.info('How quickly daft jumping zebras vex.')
    logger.warning('Jail zesty vixen who grabbed pay from quack.')
    logger.debug('Quick zephyrs blow, vexing daft Jim.')
    logger.error('The five boxing wizards jump quickly.')

    print('done logging.')
    
    # must call logging shutdown for handler to close.
    # logging.shutdown()


def cmdargs():
    import argparse

    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]

    parser = argparse.ArgumentParser(
        description="%s runs SSH logging client example" % progname)
    parser.add_argument('-p', '--port', type=int, required=True,
                        help="""Port for logging server.""")
    args = parser.parse_args()
    print(args)
    return args


if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    args = cmdargs()
    main(**vars(args))
