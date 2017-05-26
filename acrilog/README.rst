========
acrislog
========

----------------------
Multiprocessing logger
----------------------

.. contents:: Table of Contents
   :depth: 2

Overview
========

    **acrilog** is a python library encapsulating multiprocessing logging into practical use.
    
    **acrilog** started as Acrisel's internal utility for programmers.
    
    It included:
        1. Time and size rotating handler.
        #. Multiprocessing logging queue server
    
    We decided to contribute this library to Python community as a token of appreciation to
    what this community enables us.
    
    We hope that you will find this library useful and helpful as we find it.
    
    If you have comments or insights, please don't hesitate to contact us at support@acrisel.com
    

TimedSizedRotatingHandler
=========================
	
    Use TimedSizedRotatingHandler is combining TimedRotatingFileHandler with RotatingFileHandler.  
    Usage as handler with logging is as defined in Python's logging how-to
	
example
-------

    .. code-block:: python
	
        import logging
	
        # create logger
        logger = logging.getLogger('simple_example')
        logger.setLevel(logging.DEBUG)
	
        # create console handler and set level to debug
        ch = logging.TimedRotatingFileHandler()
        ch.setLevel(logging.DEBUG)
	
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	
        # add formatter to ch
        ch.setFormatter(formatter)
	
        # add ch to logger
        logger.addHandler(ch)
	
        # 'application' code
        logger.debug('debug message')
        logger.info('info message')
        logger.warn('warn message')
        logger.error('error message')
        logger.critical('critical message')	

MpLogger and LevelBasedFormatter
================================

    Multiprocessor logger using QueueListener and QueueHandler
    It uses TimedSizedRotatingHandler as its logging handler

    It also uses acris provided LevelBasedFormatter which facilitate message formats
    based on record level.  LevelBasedFormatter inherent from logging.Formatter and
    can be used as such in customized logging handlers. 
	
example
-------

Within main process
~~~~~~~~~~~~~~~~~~~

    .. code-block:: python
	
        import time
        import random
        import logging
        from acris import MpLogger
        import os
        import multiprocessing as mp

        def subproc(limit=1, logger_info=None):
            logger=MpLogger.get_logger(logger_info, name="acrilog.subproc", )
    		for i in range(limit):
                sleep_time=3/random.randint(1,10)
                time.sleep(sleep_time)
                logger.info("proc [%s]: %s/%s - sleep %4.4ssec" % (os.getpid(), i, limit, sleep_time))

        level_formats={logging.DEBUG:"[ %(asctime)s ][ %(levelname)s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                        'default':   "[ %(asctime)s ][ %(levelname)s ][ %(message)s ]",
                        }
    
        mplogger=MpLogger(logging_level=logging.DEBUG, level_formats=level_formats, datefmt='%Y-%m-%d,%H:%M:%S.%f')
        mplogger.start()

        logger.debug("starting sub processes")
        procs=list()
        for limit in [1, 1]:
            proc=mp.Process(target=subproc, args=(limit, mplogger.logger_info(),))
            procs.append(proc)
            proc.start()
    
        for proc in procs:
            if proc:
                proc.join()
    
        logger.debug("sub processes completed")

        mplogger.stop()	
        
Within individual process
~~~~~~~~~~~~~~~~~~~~~~~~~

    .. code-block:: python
	
        import logging
	
        logger=logging.getLogger(__name__)
        logger.debug("logging from sub process")
    
Example output
--------------

    .. code-block:: python

        [ 2016-12-19,11:39:44.953189 ][ DEBUG ][ starting sub processes ][ mplogger.<module>(45) ]
        [ 2016-12-19,11:39:45.258794 ][ INFO ][ proc [932]: 0/1 - sleep  0.3sec ]
        [ 2016-12-19,11:39:45.707914 ][ INFO ][ proc [931]: 0/1 - sleep 0.75sec ]
        [ 2016-12-19,11:39:45.710487 ][ DEBUG ][ sub processes completed ][ mplogger.<module>(56) ]
     
     
Change History
==============

    0.9: add ability to pass logger_info to subprocess
        
Next Steps
==========

    1. Cluster support using TCP/IP 
    #. Logging monitor and alert