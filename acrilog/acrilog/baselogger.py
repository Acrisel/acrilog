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
import os
import multiprocessing as mp
from copy import copy
from acrilib import TimedSizedRotatingHandler, get_file_handler
from datetime import datetime
import sys   
import socket
import traceback
from acrilib import LevelBasedFormatter
from copy import deepcopy 
     

    
def create_stream_handler(logging_level=logging.INFO, level_formats={}, datefmt=None):
    handlers=list()
    
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    #stdout_handler.setLevel(logging_level)
    formatter = LevelBasedFormatter(level_formats=level_formats,datefmt=datefmt) 
    stdout_handler.setFormatter(formatter)
    handlers.append(stdout_handler)
    
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    
    return handlers


class BaseLogger(object):
    ''' Builds Multiprocessing logger such all process share the same logging mechanism 
    '''
    
    kwargs_defaults = {
        'logdir': '/tmp',
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
    
    logger_info_defaults = {
        'level_formats': {
                logging.DEBUG: "[ %(asctime)-15s ][ %(host)s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                'default': "[ %(asctime)-15s ][ %(host)s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ]",
                },
         'datefmt': '%Y-%m-%d,%H:%M:%S.%f',
         'handler_kwargs': kwargs_defaults,
            }
    
    def __init__(self, name=None, logging_level=logging.INFO, level_formats={}, datefmt=None, console=False, handlers=[], *args, **kwargs):
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
        self.level_formats = level_formats if level_formats else BaseLogger.logger_info_defaults['level_formats']
        self.datefmt = datefmt if datefmt else BaseLogger.logger_info_defaults['datefmt']
        self.record_formatter = LevelBasedFormatter(level_formats=self.level_formats, datefmt=self.datefmt)
        self.logger_initialized = False
        self.handlers = handlers
        #self.process_key = process_key
        #self.consolidate = consolidate
        self.console = console
        self.name = name if name is not None else 'logger'
        self.handler_kwargs = copy(BaseLogger.kwargs_defaults)
        self.handler_kwargs.update(kwargs)
        self.handler_args = args
        #self.encoding=encoding
        #self.file_mode=file_mode
        #self.local_log = local_log
        
    def global_file_handlers(self,):
        #if not process_key: process_key=self.name
        #handlers = get_file_handler(logging_level=self.logging_level, formatter=self.record_formatter, **self.kwargs)
        handlers = get_file_handler(formatter=self.record_formatter, **self.kwargs)
        self.global_filename = handlers[0].filename
        return handlers
        #for handler in handlers:
        #    self.queue_listener.addHandler(handler)  
            
    #def add_file_handlers(cls, name, logger, logdir, logging_level,  record_formatter, **kwargs):
    @classmethod
    def add_file_handlers(cls, logger,  record_formatter, **kwargs):
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
        #global_handlers = get_file_handler(logging_level=logging_level, formatter=record_formatter, **kwargs)
        global_handlers = get_file_handler(formatter=record_formatter, **kwargs)
        
        for handler in global_handlers:
            logger.addHandler(handler) 
            
    @classmethod
    def base_info(cls, log_info):
        keys = [
            'name',
            'logging_level',
            'level_formats',
            'datefmt',
            'handler_kwargs',
            'server_host',
            ]
        result = dict([(k,log_info[k]) for k in keys])
        return result
            
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
        
        # TODO: CHANGE TO USE MergedChainedDict
        defaults = deepcopy(BaseLogger.logger_info_defaults)
        defaults.update(logger_info)
        logger_info = defaults
        # The only handler desired is the SubProcessLogHandler.  If any others
        # exist, remove them. In this case, on Unix and Linux the StreamHandler
        # will be inherited.
    
        #for handler in logger.handlers:
        #    # just a check for my sanity
        #    assert not isinstance(handler, TimedSizedRotatingHandler)
        #    logger.removeHandler(handler)
        this_host = socket.gethostbyname(socket.gethostname())
        
        # server may already started logger
        # if logger_info['server_host'] == server_host: return logger
        
        #loggerq=logger_info['loggerq']
        #queue_handler = QueueHandler(loggerq)
        #logger.addHandler(queue_handler)

        # add the handler only if processing locally and this host is not server host.
        
        if logger_info['server_host'] != this_host:
            level_formats = logger_info['level_formats']
            datefmt = logger_info['datefmt']
            cls.add_file_handlers(name=name, 
                                  #process_key=logger_info['process_key'], 
                                  logger=logger,
                                  #logdir=logger_info['logdir'], 
                                  #logging_level=logging_level,
                                  record_formatter=LevelBasedFormatter(level_formats=level_formats, datefmt=datefmt),
                                  **logger_info['handler_kwargs'],
                                  )
        
        # On Windows, the level will not be inherited.  Also, we could just
        # set the level to log everything here and filter it in the main
        # process handlers.  For now, just set it from the global default.
        logging_level = logger_info['logging_level']
        logger.setLevel(logging_level)     
        return logger

    
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
