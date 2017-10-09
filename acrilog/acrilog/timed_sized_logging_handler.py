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

from logging import INFO, Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os

class TimedSizedRotatingHandler(TimedRotatingFileHandler, RotatingFileHandler):
    
    def __init__(self, filename, file_mode='a', maxBytes=0, backupCount=0, encoding='ascii', delay=False, when='h', interval=1, utc=False, atTime=None, *args, **kwargs):
        """ 
        Combines RotatingFileHandler TimedRotatingFileHandler)  
        """
        
        if file_mode.startswith('w'):
            try: os.remove(filename)
            except: pass
        self.filename=filename
        RotatingFileHandler.__init__(self, filename=filename, mode=file_mode, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding, delay=delay)
        TimedRotatingFileHandler.__init__(self, filename=filename, when=when, interval=interval, backupCount=backupCount, encoding=encoding, delay=delay, utc=utc, atTime=atTime)
        
    def shouldRollover(self, record):
        """
        Check the need to rotate.     
        """
        timed_rollover = TimedRotatingFileHandler.shouldRollover(self, record) 
        sized_rollover = RotatingFileHandler.shouldRollover(self, record)
        
        return timed_rollover or sized_rollover

    def doRollover(self):
        """
        It is enough to use timed base rollover.
        """
        super(TimedRotatingFileHandler, self).doRollover()

    def getFilesToDelete(self):
        """
        It is enough to use timed base rollover.
        """
        return super(TimedRotatingFileHandler, self).getFilesToDelete()        


from acrilog.formatters import LevelBasedFormatter
def get_file_handler(logdir='', name=None, formatter=None, file_prefix=None, file_suffix=None, *args, **kwargs):
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
    
    if logdir:
        if not os.path.isdir(logdir):
            try:
                os.makedirs(logdir, mode=0o744, exist_ok=True)
            except:
                raise

    #key_s=''
    if file_suffix: name = "%s.%s" %(name, file_suffix)
    if name: name = "%s.log" % name
    else: name = 'logger.log'
    if file_prefix: name = "%s.%s" %(file_prefix, name)
    
    #print('get_file_handlers: process_key:', process_key)
    #traceback.print_stack()
    filename = os.path.join(logdir, name)
    #del kwargs['delay']
    handler = TimedSizedRotatingHandler(filename=filename, **kwargs)
    #handler.setLevel(logging_level)
    #formatter = formatter if formatter is not None else LevelBasedFormatter(level_formats=level_formats, datefmt=datefmt)
    #print('get_file_handler formatter:', formatter)
    if formatter is None: raise
    handler.setFormatter(formatter)
    result.append(handler)
    # create error file handler and set level to error
    
    return result

class HierarchicalTimedSizedRotatingHandler(Handler):
    def __init__(self, key='name', separator='.', consolidate='', *args, **kwargs):
        ''' Maintains TimedSizedRotatingHandler handlers according to hierarchy.
        
        LogRecord key will be used to store and fetch handlers.
        If there is separator, value of LogRecord key will be split from the right generating multiple values.
        E.g., A.B.C value with be translated to hierarchical values of A, A.B, and A.B.C.
        Note, it is important that LogRecord key values will not include separator characters.
        
        Args:
            key: name of LogRecord attributes to use to associate handlers.
            separator: is used to split key to hierarchy. If None, key value will not be broken to parts.
            consolidate: name to which records will be consolidated into.
            
            kwargs: 
                logdir='', 
                name=None, 
                formatter=None, 
                file_prefix=None, 
                file_suffix=None
                
                filename, 
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
        super(HierarchicalTimedSizedRotatingHandler, self).__init__() 

        self.separator = separator
        self.key = key
        self.consolidate = consolidate
        self.handler_args = args
        self.handler_kwargs = kwargs
        self.__handlers = dict()
        
    def handle(self, record):
        """ Override handle a record.  Loops through handlers according to key hierarchy offering them the record
        to handle.

        Args:
            record: The record to handle.
        """
        
        # Find handlers that match process keys
        
        #attributes = record.__dict__
        #record_name = attributes.get('name', None)
        record_name = getattr(record, 'name')
        #for process_key in self.process_key:
        #record_key = attributes.get(self.key, None)
        try: record_key = getattr(record, self.key)
        except KeyError: record_key = ''
        #print('record_key[process_key]: %s[%s]' %(record_key, self.key))
        #print('record_key[processName]: %s' %(repr(record.__dict__)))
        
        keys = [record_key]
        if self.consolidate: keys.append(self.consolidate)
        if self.separator is not None:
            keys = []
            left_key = record_key
            while left_key:
                keys.append(left_key)
                left_key = left_key.rpartition(self.separator)[0]
        
        #print('consolidate keys %s: %s' % (record_key, keys))
        handlers = list()
        for record_key in keys:
            #if record_key: 
            #process_handlers = self.handlers[process_key]
            key_handlers = self.__handlers.get(record_key,)
            # avoid getting dedicated handler when in consolidated mode and record with 
            # name equal to the global.
            need_handler = key_handlers is None or record_key != self.name 
            if need_handler:
                key_handlers = get_file_handler(*self.handler_args, name=record_key, **self.handler_kwargs)
                self.__handlers[record_key] = key_handlers
                
            handlers.extend(key_handlers)
                
        #if len(self.global_handlers) > 0:
        #    handlers.extend(self.global_handlers)
            
        #if len(self.console_handlers) > 0:
        #    handlers.extend(self.console_handlers)
        
        record = self.prepare(record)
        
        for handler in list(set(handlers)):
            if record.levelno >= handler.level: # This check is not in the parent class
                handler.handle(record)
                
    def prepare(self, record):
        return record

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
        #if not key_bind:
        #    self.global_handlers.append(handler)

    def removeHandler(self, hdlr):
        """
        Remove the specified handler from this logger.
        """
        if hdlr in self.handlers:
            hdlr.close()
            self.handlers.remove(hdlr)
        
        
        
        
        