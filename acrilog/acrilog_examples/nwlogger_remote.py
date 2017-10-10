#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import NwLogger
import multiprocessing as mp
import logging
from acrilog import NwLoggerClientHandler
import os
import time

module_logger = logging.getLogger(__name__)
module_logger.addHandler(logging.StreamHandler())
module_logger.setLevel(logging.DEBUG)
                    
def main(port):
    
    logger_info = {
        'name': 'example.e1',
        'port': port,
        'logging_level': logging.DEBUG,
        'server_host': 'arnon-mbp',
        }
    handler = NwLoggerClientHandler(logger_info=logger_info, ssh_host='arnon-mbp-acris') #, logger=module_logger)
    logger = logging.getLogger('example.e1')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    time.sleep(30)
    
    logger.info('How quickly daft jumping zebras vex.')
    logger.warning('Jail zesty vixen who grabbed pay from quack.')
    logger.debug('Quick zephyrs blow, vexing daft Jim.')
    logger.error('The five boxing wizards jump quickly.')
    
    logger.close()
    
def cmdargs():
    import argparse
    
    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]
    
    parser = argparse.ArgumentParser(description="%s runs SSH logging client example" % progname)
    parser.add_argument('-p', '--port', type=int, default=49740,
                        help="""Port for logging server.""")
    args = parser.parse_args()  
    
    return args
    

     
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    args = cmdargs()
    main(**vars(args))
