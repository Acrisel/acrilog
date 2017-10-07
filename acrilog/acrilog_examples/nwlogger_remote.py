#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import NwLogger
import multiprocessing as mp
import logging
from acrilog import NwLoggerClientHandler

module_logger = logging.getLogger(__name__)
module_logger.addHandler(logging.StreamHandler())
module_logger.setLevel(logging.DEBUG)
                    
def main():
    
    logger_info = {
        'name': 'example.e1',
        'port': 49740,
        'logging_level': 10,
        }
    handler = NwLoggerClientHandler(logger_info=logger_info, ssh_host='arnon-mbp-acris', logger=module_logger)
    logger = logging.getLogger('example.e1')
    logger.addHandler(handler)
    
    logger.info('How quickly daft jumping zebras vex.')
    logger.warning('Jail zesty vixen who grabbed pay from quack.')
    logger.debug('Quick zephyrs blow, vexing daft Jim.')
    logger.error('The five boxing wizards jump quickly.')
    
    handler.close()
     
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    main()
