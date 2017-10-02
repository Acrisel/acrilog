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

import logging
from logging.handlers import QueueListener, QueueHandler
import os
import multiprocessing as mp
from copy import copy
from acrilog.timed_sized_logging_handler import TimedSizedRotatingHandler
from datetime import datetime
import sys   
import socket
import traceback
from acrilog.formatters import LevelBasedFormatter
from acrilog.utils import get_hostname, get_ip_address
     
     
class LoggerAddHostFilter(logging.Filter):
    """
    This is filter adds host information to LogRecord.
    """

    #USERS = ['jim', 'fred', 'sheila']
    #IPS = ['123.231.231.123', '127.0.0.1', '192.168.0.1']

    def filter(self, record):

        if not hasattr(record, 'host'):
            record.host = get_hostname()
            record.ip = get_ip_address()
        return True

    
def create_stream_handler(logging_level=logging.INFO, level_formats={}, datefmt=None):
    handlers=list()
    
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    #stdout_handler.setLevel(logging_level)
    formatter = LevelBasedFormatter(level_formats=level_formats,datefmt=datefmt) 
    stdout_handler.setFormatter(formatter)
    handlers.append(stdout_handler)
    
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    
    return handlers


def get_file_handler(logdir='', logging_level=logging.INFO, process_key=None, formatter=None, file_prefix=None, file_suffix=None, **kwargs):
    '''
    
    Args:
        kwargs:
            file_mode='a', 
            maxBytes=0, 
            backupCount=0, 
            encoding='ascii', 
            delay=False, 
            when='h', 
            interval=1, 
            utc=False, 
            atTime=None
    '''
    result=list()
    if logdir is None: logdir=''
    
    #key_s=''
    if file_suffix: process_key = "%s.%s" %(process_key, file_suffix)
    if process_key: name = "%s.log" % process_key
    else: name = 'mplogger.log'
    if file_prefix: name = "%s.%s" %(file_prefix, name)
    
    
    #print('get_file_handlers: process_key:', process_key)
    #traceback.print_stack()
    filename = os.path.join(logdir, name)
    #handler = TimedSizedRotatingHandler(filename=filename, delay="true", **kwargs)
    handler = TimedSizedRotatingHandler(filename=filename, **kwargs)
    #handler.setLevel(logging_level)
    handler.setFormatter(formatter)
    result.append(handler)
    # create error file handler and set level to error
    
    return result

class BaseLogger(object):
    ''' Builds Multiprocessing logger such all process share the same logging mechanism 
    '''
    
    kwargs_defaults = {
        'key':'name',
        'file_mode': 'a', 
        'file_prefix': '',
        'file_suffix': '',
        'maxBytes': 0, 
        'backupCount': 0, 
        'encoding': 'ascii', 
        'delay': False, 
        'when':'h', 
        'interval': 1, 
        'utc': False, 
        'atTime': None,
       }
    
    def __init__(self, name='logger', logging_level=logging.INFO, level_formats={}, datefmt=None, console=True, handlers=[], *args, **kwargs):
        '''Initiates MpLogger service
        
        Args:
            name: base name to use for file logs.
            logdir: folder to which log files will be written; if not provided, log files will not be created
            logging_level: level from which logging will be done 
            level_formats: mapping of logging levels to formats to use for constructing message
            datefmt: date format to use
            process_key: list of record names that would be used to create files
            console_name: when set, records assigned to process_key handler will also routed to global handlers.
            #logging_root: defaults to name if not provided
            encoding: used in defining file handlers; default 'ascii'
            handlers: list of global handlers 
            kwargs: pass-through to handler defining its policy
                key='name',
                file_mode='a', 
                file_prefix='',
                file_suffix='',
                maxBytes=0, 
                backupCount=0, 
                delay=False, 
                when='h', 
                interval=1, 
                utc=False, 
                atTime=None

        '''
                    
        self.logging_level = logging_level
        self.level_formats = level_formats
        self.datefmt = datefmt
        self.record_formatter = LevelBasedFormatter(level_formats=level_formats, datefmt=datefmt)
        self.logger_initialized = False
        self.handlers = handlers
        #self.process_key = process_key
        #self.consolidate = consolidate
        self.console = console
        self.name = name
        self.handler_kwargs = copy(BaseLogger.kwargs_defaults)
        self.handler_kwargs.update(kwargs)
        self.handler_args = args
        #self.encoding=encoding
        #self.file_mode=file_mode
        #self.local_log = local_log
        
    def global_file_handlers(self,):
        #if not process_key: process_key=self.name
        handlers = get_file_handler(logging_level=self.logging_level, formatter=self.record_formatter, **self.kwargs)
        self.global_filename = handlers[0].filename
        return handlers
        #for handler in handlers:
        #    self.queue_listener.addHandler(handler)  
            
    @classmethod
    def add_file_handlers(cls, name, logger, logdir, logging_level,  record_formatter, **kwargs):
        '''
        Args:
            kwargs:
                file_mode='a', 
                maxBytes=0, 
                backupCount=0, 
                encoding='ascii', 
                delay=False, 
                when='h', 
                interval=1, 
                utc=False, 
                atTime=None
        '''
        #if not process_key: process_key=name
        global_handlers = get_file_handler(logging_level=logging_level, formatter=record_formatter, **kwargs)
        
        for handler in global_handlers:
            logger.addHandler(handler)  
            
    def logger_info(self):
        hostname = socket.gethostbyname(socket.gethostname())
        info = {'name': self.name,
                #'process_key': self.process_key,
                #'logdir': self.logdir, 
                'logging_level': self.logging_level,
                'level_formats': self.level_formats,
                'datefmt': self.datefmt,
                'handler_kwargs': self.handler_kwargs,
                'server_host': hostname,
               }
        return info
            
    @classmethod
    def get_logger(cls, logger_info, name):
        # create the logger to use.
        logger = logging.getLogger(name)
        logger.propagate = False
        # The only handler desired is the SubProcessLogHandler.  If any others
        # exist, remove them. In this case, on Unix and Linux the StreamHandler
        # will be inherited.
    
        #for handler in logger.handlers:
        #    # just a check for my sanity
        #    assert not isinstance(handler, TimedSizedRotatingHandler)
        #    logger.removeHandler(handler)
        server_host = socket.gethostbyname(socket.gethostname())
        
        # server may already started logger
        # if logger_info['server_host'] == server_host: return logger
        
        logging_level = logger_info['logging_level']
        #loggerq=logger_info['loggerq']
        #queue_handler = QueueHandler(loggerq)
        #logger.addHandler(queue_handler)

        # add the handler only if processing locally and this host is not server host.
        
        if logger_info['server_host'] != server_host:
            level_formats = logger_info['level_formats']
            datefmt = logger_info['datefmt']
            cls.add_file_handlers(name=name, process_key=logger_info['process_key'], 
                                  logger=logger,
                                  logdir=logger_info['logdir'], 
                                  logging_level=logging_level,
                                  record_formatter=LevelBasedFormatter(level_formats=level_formats, datefmt=datefmt),
                                  **logger_info['handler_kwargs'],
                                  )
        
        # On Windows, the level will not be inherited.  Also, we could just
        # set the level to log everything here and filter it in the main
        # process handlers.  For now, just set it from the global default.
        logger.setLevel(logging_level)     
        return logger

    
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
