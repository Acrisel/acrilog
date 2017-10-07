#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import NwLogger
import multiprocessing as mp
import logging
from acrilog import NwLoggerClientHandler
                    
def main():
    
    logger_info = {
        'name': 'example.e1',
        'port': 49740,
        'logging_level': 10,
        }
    handler = NwLoggerClientHandler(logger_info=logger_info, ssh_host='arnon-mbp-acris',)
    logger = logging.getLogger('example.e1')
    logger.addHandler(handler)
    
    logger.info('How quickly daft jumping zebras vex.')
    logger.warning('Jail zesty vixen who grabbed pay from quack.')
    logger.debug('Quick zephyrs blow, vexing daft Jim.')
    logger.error('The five boxing wizards jump quickly.')
     
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    main()
