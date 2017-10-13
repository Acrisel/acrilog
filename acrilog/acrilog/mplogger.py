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
import multiprocessing as mp
from acrilog.baselogger import BaseLogger, create_stream_handler
from acrilib import LoggerAddHostFilter, HierarchicalTimedSizedRotatingHandler


class LogRecordQueueListener(QueueListener):
    def __init__(self, queue,): # *handlers):
        super(LogRecordQueueListener, self).__init__(queue,)# *handlers)
        
    def handle(self, record):
        name = record.name
        logger = logging.getLogger(name)
        record = self.prepare(record)
        logger.handle(record)

    def start_server_until_stopped(self, abort):
        self.start()
        abort.wait()
        self.stop()


def start_mplogger(name=None, loggerq=None, logging_level=None, formatter=None, level_formats=None, datefmt=None, console=False, started=None, abort=None, finished=None, args=(), kwargs={},):
    #logger = logging.getLogger(name=self.logging_root)
    logger = logging.getLogger(name=name)
    logger.setLevel(logging_level)
    logger.addFilter(LoggerAddHostFilter())
    
    #queue_handler = LogRecordQueueHandler(loggerq)
    #logger.addHandler(queue_handler)
    
    handlers = [HierarchicalTimedSizedRotatingHandler(*args, formatter=formatter, **kwargs)]
    if console:
        console_handlers = create_stream_handler(logging_level=logging_level, level_formats=level_formats, datefmt=datefmt)            
        handlers.extend(console_handlers)
        
    for handler in handlers:
        logger.addHandler(handler)
            
    queue_listener = LogRecordQueueListener(loggerq,) # *handlers)
    #queue_listener = LogRecordQueueListener(loggerq, name=name, logging_level=logging_level, logdir=logdir, formatter=record_formatter, process_key=process_key, global_handlers=ghandlers, **kwargs)
            
    started.set()
    queue_listener.start_server_until_stopped(abort)
    #logger_name=name
    #logger = logging.getLogger(name=logger_name) #if get else None
    #return queue_listener
    finished.set()

class MpLogger(BaseLogger):
    ''' Builds Multiprocessing logger such all process share the same logging mechanism 
    '''
    def __init__(self, name='logger', logging_level=logging.INFO, *args, **kwargs):
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
            kwargs: pass-through to hierarchical handler defining its policy
                key='name' 
                separator='.'
                consolidate=''
                file_mode='a', 
                file_prefix='',
                file_suffix='',
                maxBytes=0, 
                backupCount=0, 
                encoding='ascii', 
                delay=False, 
                when='h', 
                interval=1, 
                utc=False, 
                atTime=None

        '''
        super(MpLogger, self).__init__(*args, name=name, logging_level=logging_level, **kwargs)
            
        self.queue_listener = None
        self.abort = None
        #self.args = args
        #self.kwargs = kwargs
        self.logger_initialized = False
                                        
    def logger_info(self):
        info = super(MpLogger, self).logger_info()
        info.update({
                'loggerq': self.loggerq,
               })
        return info
            
    @classmethod
    def get_logger(cls, logger_info, name=None):
        name = name if name is not None else logger_info['name']
        # create the logger to use.
        logger = BaseLogger.get_logger(logger_info, name)
        logger.addFilter(LoggerAddHostFilter())
        loggerq = logger_info['loggerq']
        
        # check logger has already proper handlers or not
        already_set = False
        for handler in logger.handlers:
            if isinstance(handler, QueueHandler):
                already_set = already_set or (handler.queue == loggerq)
        
        if not already_set:        
            queue_handler = QueueHandler(loggerq)
            logger.addHandler(queue_handler)

        return logger

    def start(self, name=None, ):
        ''' starts logger for multiprocessing using queue.
        
        Args:
            name: identify starting process to allow it log into its own logger 

        Returns:
            logger: set with correct Q handler
        '''
        # create console handler and set level to info
        
        #if MpLogger.logger_initialized:
        if self.logger_initialized:
            return
        self.logger_initialized=True
        
        #self.manager = mp.Manager()
        #self.controller = self.manager.Namespace()
        manager=mp.Manager()    
        self.loggerq = manager.Queue()

        self.abort = mp.Event()
        started = mp.Event()
        self.finished = mp.Event()
        
        start_nwlogger_kwargs = {
            'name': self.name if not name else name, 
            'loggerq': self.loggerq, 
            'logging_level': self.logging_level, 
            'formatter': self.record_formatter, 
            'level_formats': self.level_formats, 
            'datefmt': self.datefmt, 
            'console': self.console,
            'started': started, 
            'abort': self.abort, 
            'finished': self.finished,   
            'args': self.handler_args, 
            'kwargs': self.handler_kwargs,
            }
        self.logger_proc = mp.Process(target=start_mplogger, kwargs=start_nwlogger_kwargs, daemon=True)
        self.logger_proc.start()
        
        started.wait()        

    def stop(self,):
        if self.abort:
            self.abort.set()
            self.finished.wait()
            if self.logger_proc.is_alive():
                #print('Joining logger.')
                self.logger_proc.join()
        #print('Stopped logger.')
        
        
    '''    
    def stop(self,):
        if self.queue_listener:
            self.queue_listener.stop()
            
    def quite(self,):
        if self.queue_listener:
            self.queue_listener.enqueue_sentinel()
    '''
                
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
