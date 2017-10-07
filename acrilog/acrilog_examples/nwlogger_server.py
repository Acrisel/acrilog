#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import NwLogger
import multiprocessing as mp
import logging
import time
import os

config_file = os.path.abspath('logger.conf')
# because OSX adds /var -> /private/var
if config_file.startswith('/private'):
    config_file = config_file[8:]
          
                    
def main():
    #logging_config = config.get('LOGGING')
    nwlogger = NwLogger('example', logging_level=logging.DEBUG, console=True, consolidate=True, port=49740)
    nwlogger.start()
    
    print("Logger host, port: {}, {}".format(nwlogger.host, nwlogger.port))
    
    time.sleep(60)
    
    nwlogger.stop()

    
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    main()
