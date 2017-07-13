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


class MpQueueListener(QueueListener):
    def __init__(self, queue, name=None, logging_level=logging.INFO, logdir=None, formatter=None, process_key=['processName'], global_handlers=[], **kwargs):
        super(MpQueueListener, self).__init__(queue, *global_handlers)
        """ Initialize an instance with the specified queue and
        handlers.
        
        Args:
            handlers: list of handlers to apply
            process_key: list of keys by which to bind handler to records.
                handlers that don't have any key are classified as global handlers.
                if record doens't have any matching key, global handlers will be used.
                if records match, only matching handlers will be used. 
        """
        self.process_key=process_key
        self.logdir=logdir
        self.formatter=formatter
        self.name=name
        self.kwargs=kwargs
        
        key_handlers=dict([(p, dict()) for p in process_key])
                    
        self.key_handlers=key_handlers
        self.global_handlers=global_handlers
        self.console_handlers=list()
        self.logging_level=logging_level
        
    def handle(self, record):
        """ Override handle a record.

        This just loops through the handlers offering them the record
        to handle.

        Args:
            record: The record to handle.
        """
        
        # Find handlers that match process keys
        handlers=list()
        record_name=record.__dict__.get('name', None)
        for process_key in self.process_key:
            record_key=record.__dict__.get(process_key, None)
            #print('record_key[process_key]: %s[%s]' %(record_key, process_key))
            #print('record_key[processName]: %s' %(repr(record.__dict__)))
            if record_key: 
                process_handlers=self.key_handlers[process_key]
                key_handlers=process_handlers.get(record_key, [])
                
                # avoid getting dedicated handler in special case when in consolidated mode and record with 
                # name equal to the global one (QueueListiner name)
                need_handler=len(key_handlers) ==0 and (record_key != self.name or len(self.global_handlers) ==0)
                if need_handler:
                    name=record_name
                    #file_prefix=self.kwargs.get('file_prefix')
                    #if file_prefix is None: file_prefix=name
                    #print('file_prefix, record_key, record_name:', file_prefix, record_key, record_name)
                    if record_name != record_key:
                        name="%s.%s" % (name, record_key)
                    key_handlers=get_file_handler(logging_level=self.logging_level, logdir=self.logdir, process_key=name, formatter=self.formatter, **self.kwargs)
                    process_handlers[record_key]=key_handlers
                handlers.extend(key_handlers)
                
        
        if len(self.global_handlers) > 0:
            handlers.extend(self.global_handlers)
            
        if len(self.console_handlers) > 0:
            handlers.extend(self.console_handlers)
        
        record = self.prepare(record)
        
        for handler in list(set(handlers)):
            if record.levelno >= handler.level: # This check is not in the parent class
                handler.handle(record)

    def addConsoleHandler(self, handler):
        self.console_handlers.append(handler)
        
    def addHandler(self, handler):
        """
        Add the specified handler to this logger.
        
        handler is expected to have process_key attribute.
        process_key attribute is expected to be a list of records attribute names that handler would bind to.
        if handler does not have process_key attribute or it is empty, handler will be associated with 
        """
        key_bind=False
        if hasattr(handler, 'process_key'):
            handler_key=handler.process_key
            for key in list(set(self.process_key) & set(handler_key)):
                exist_handler=self.key_handlers.get(key, list())
                self.key_handlers[key]=exist_handler
                exist_handler.append(handler)
                key_bind=True
        if not key_bind:
            self.global_handlers.append(handler)

    def removeHandler(self, hdlr):
        """
        Remove the specified handler from this logger.
        """
        if hdlr in self.handlers:
            hdlr.close()
            self.handlers.remove(hdlr)
            
class MicrosecondsDatetimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        
        if ct is  None:
            ct=datetime.now()
            
        if datefmt is not None:
            s = ct.strftime(datefmt)
        else:
            #print('MicrosecondsDatetimeFormatter:', repr(ct),)
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
            
        return s
            
class LevelBasedFormatter(logging.Formatter):
    
    defaults={
        logging.DEBUG : u"%(asctime)-15s: %(process)-7s: %(levelname)-7s: %(message)s: %(module)s.%(funcName)s(%(lineno)d)",
        'default' : u"%(asctime)-15s: %(process)-7s: %(levelname)-7s: %(message)s",
        }
 
    def __init__(self, level_formats={}, datefmt=None):
        defaults=LevelBasedFormatter.defaults
        if level_formats:
            defaults=copy(LevelBasedFormatter.defaults)
            defaults.update(level_formats)
            
        self.datefmt=datefmt  
        self.defaults=dict([(level, MicrosecondsDatetimeFormatter(fmt=fmt, datefmt=self.datefmt)) for level, fmt in defaults.items()])
        self.default_format=self.defaults['default']  
        logging.Formatter.__init__(self, fmt=self.default_format, datefmt=self.datefmt)

    def format(self, record):
        formatter=self.defaults.get(record.levelno, self.default_format,)
        result = formatter.format(record)
        return result
    
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
    if file_suffix: process_key="%s.%s" %(process_key, file_suffix)
    if process_key: name="%s.log" % process_key
    else: name='mplogger.log'
    if file_prefix: name="%s.%s" %(file_prefix, name)
    
    
    #print('get_file_handlers: process_key:', process_key)
    #traceback.print_stack()
    filename=os.path.join(logdir, name)
    handler = TimedSizedRotatingHandler(filename=filename, delay="true", **kwargs)
    #handler.setLevel(logging_level)
    handler.setFormatter(formatter)
    result.append(handler)
    # create error file handler and set level to error
    
    return result

class MpLogger(object):
    ''' Builds Multiprocessing logger such all process share the same logging mechanism 
    '''
    #def __init__(self, name='mplogger', logdir=None, logging_level=logging.INFO, level_formats={}, datefmt=None, process_key=['name'], console=True, consolidate=False, local_log=True, logging_root=None, handlers=[], **kwargs):
    def __init__(self, name='mplogger', logdir=None, logging_level=logging.INFO, level_formats={}, datefmt=None, process_key=['name'], console=True, consolidate=False, local_log=True, handlers=[], **kwargs):
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
        
        self.logdir=logdir
        if not os.path.isdir(logdir):
            try:
                os.makedirs(logdir, mode=0o744, exist_ok=True)
            except:
                raise
            
        self.logging_level=logging_level
        self.level_formats=level_formats
        self.datefmt=datefmt
        self.record_formatter=LevelBasedFormatter(level_formats=level_formats, datefmt=datefmt)
        #self.logging_root=logging_root if logging_root is not None else name
        self.logger_initialized=False
        self.queue_listener=None
        self.handlers=handlers
        self.process_key=process_key
        self.consolidate=consolidate
        self.console=console
        self.name=name
        self.kwargs=kwargs
        #self.encoding=encoding
        #self.file_mode=file_mode
        self.local_log=local_log
        
    def _global_file_handlers(self,):
        #if not process_key: process_key=self.name
        handlers=get_file_handler(logdir=self.logdir, logging_level=self.logging_level, process_key=self.name, formatter=self.record_formatter, **self.kwargs)
        self.global_filename=handlers[0].filename
        return handlers
        #for handler in handlers:
        #    self.queue_listener.addHandler(handler)  
            
    @classmethod
    def add_file_handlers(cls, name, logger, logdir, logging_level,  record_formatter, process_key='', **kwargs):
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
        if not process_key: process_key=name
        global_handlers=get_file_handler(logdir=logdir, logging_level=logging_level, process_key=process_key, formatter=record_formatter, **kwargs)
        
        for handler in global_handlers:
            logger.addHandler(handler)  
            
    def logger_info(self):
        return {'process_key': self.process_key,
                'logdir': self.logdir, 
                'logging_level': self.logging_level,
                'record_formatter': self.record_formatter,
                'record_formatter': self.record_formatter,
                'loggerq': self.loggerq,
                'handler_kwargs': self.kwargs,
                'local_log': self.local_log,
                'server_host': socket.gethostbyname(socket.gethostname()),
               }
            
    @classmethod
    def get_logger(cls, logger_info, name):
        # create the logger to use.
        logger = logging.getLogger(name)
        # The only handler desired is the SubProcessLogHandler.  If any others
        # exist, remove them. In this case, on Unix and Linux the StreamHandler
        # will be inherited.
    
        #for handler in logger.handlers:
        #    # just a check for my sanity
        #    assert not isinstance(handler, TimedSizedRotatingHandler)
        #    logger.removeHandler(handler)
        server_host=socket.gethostbyname(socket.gethostname())
        
        # server may already started logger
        # if logger_info['server_host'] == server_host: return logger
        
        logging_level=logger_info['logging_level']
        loggerq=logger_info['loggerq']
        queue_handler = QueueHandler(loggerq)
        logger.addHandler(queue_handler)

        # add the handler only if processing locally and this host is not server host.
        
        if logger_info['local_log'] and logger_info['server_host'] != server_host:
            cls.add_file_handlers(name=name, process_key=logger_info['process_key'], 
                                  logger=logger,
                                  logdir=logger_info['logdir'], 
                                  logging_level=logging_level,
                                  record_formatter=logger_info['record_formatter'],
                                  **logger_info['handler_kwargs'],
                                  )
        
        # On Windows, the level will not be inherited.  Also, we could just
        # set the level to log everything here and filter it in the main
        # process handlers.  For now, just set it from the global default.
        logger.setLevel(logging_level)     
        return logger

    def start(self, name=None):
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
        #logger = logging.getLogger(name=self.logging_root)
        logger = logging.getLogger(name=self.name)
        logger.setLevel(self.logging_level)
            
        manager=mp.Manager()    
        self.loggerq=manager.Queue()
        queue_handler = QueueHandler(self.loggerq)
        logger.addHandler(queue_handler)
        
        ghandlers=[]
        if self.logdir and self.consolidate: # and self.force_global:
            ghandlers=self._global_file_handlers()
        
        self.queue_listener = MpQueueListener(self.loggerq, name=self.name, logging_level=self.logging_level, logdir=self.logdir, formatter=self.record_formatter, process_key=self.process_key, global_handlers=ghandlers, **self.kwargs)
    
        if len(self.handlers) == 0:
            if self.console:
                handlers=create_stream_handler(logging_level=self.logging_level, level_formats=self.level_formats, datefmt=self.datefmt)            
                for handler in handlers:
                    self.queue_listener.addConsoleHandler(handler)
            
        else: # len(self.handlers) > 0:
            for handler in self.handlers:
                self.queue_listener.addHandler(handler)
            
        self.queue_listener.start()
        logger_name=name if name is not None else self.name
        return logging.getLogger(name=logger_name)
        
    def stop(self,):
        if self.queue_listener:
            self.queue_listener.stop()
            
    def quite(self,):
        if self.queue_listener:
            self.queue_listener.enqueue_sentinel()

if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
