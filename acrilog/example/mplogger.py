# -*- encoding: utf-8 -*-
##############################################################################
#
#    Acrisel LTD
#    Copyright (C) 2008- Acrisel (acrisel.com) . All Rights Reserved
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

import time
import random
import logging
from acrilog import MpLogger
import multiprocessing as mp
import os


def procly(limit=1, logger_info=None):
    logger=MpLogger.get_logger(logger_info, name="acrilog.procly", )
    #logger=logging.getLogger("acrilog")
    for i in range(limit):
        sleep_time=3/random.randint(1,10)
        time.sleep(sleep_time)
        logger.debug("%s/%s - sleep %4.4ssec" % (i, limit, sleep_time))

level_formats={logging.DEBUG:"[ %(asctime)-26s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                'default':   "[ %(asctime)-26s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ]",
                }

logdir=os.getcwd()
#mplogger=MpLogger(name='mplogger', logdir=logdir, logging_level=logging.DEBUG, level_formats=level_formats, datefmt='%Y-%m-%d,%H:%M:%S.%f', 
#                  process_key=['processName'], console=True, force_global=True)

if __name__=='__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    
    mplogger=MpLogger(name='acrilog', 
                      logdir='/var/acrisel/log/acrilog', 
                      logging_level=logging.DEBUG, 
                      level_formats=level_formats,
                      console=True, 
                      force_global=False,
                      datefmt='%Y-%m-%d,%H:%M:%S.%f',
                      encoding='utf8',
                      )
    logger=mplogger.start()
    
    #logger=logging.getLogger('acrilog')
    logger_info=mplogger.logger_info()
    #logger=MpLogger.get_logger(name='acrilog', logger_info=logger_info)
    
    logger.info("starting sub processes")
    procs=list()
    seq=0
    for limit in [1, 1]:
        seq+=1
        proc=mp.Process(target=procly, args=(limit, logger_info))
        proc.name='subproc-%s' % seq
        procs.append(proc)
        proc.start()
    
    
    for proc in procs:
        if proc:
            #logger.info("joining proc %s" % repr(proc))
            proc.join()
            #logger.info("joined proc %s" % repr(proc))
        
    logger.info("sub processes completed; \u2754")
    
    mplogger.stop()

    

