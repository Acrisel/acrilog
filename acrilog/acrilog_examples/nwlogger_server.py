#!/usr/bin/env python
'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import NwLogger
import multiprocessing as mp
import logging
import time

           
                    
def main():
    
    nwlogger = NwLogger('example', logging_level=logging.DEBUG, consolidate=True, port=49740)
    nwlogger.start()
    
    print("Logger host, port: {}, {}".format(nwlogger.host, nwlogger.port))
    
    time.sleep(60)
    
    nwlogger.stop()

    
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    main()
