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

import pickle
import logging
import logging.handlers
import socketserver
import struct
import multiprocessing as mp
import threading as th
from acrilog.baselogger import BaseLogger, create_stream_handler
from acrilib import LoggerAddHostFilter, get_free_port, get_hostname, get_ip_address, HierarchicalTimedSizedRotatingHandler


# TODO: get USE_QUEUE = True working without warnings at the end.
USE_QUEUE = False

class AcrilogError(Exception):
    pass

class LoggerQueueReceiver(object):
    
    ABORT='ABORT'
    
    def __init__(self, name=None, logging_level=None, formatter=None, level_formats=None, datefmt=None, console=False, args=(), kwargs={}):
        self.logger_queue = mp.Queue()
        self.name = name
        self.logging_level = logging_level
        self.formatter = formatter
        self.level_formats = level_formats
        self.datefmt = datefmt
        self.console = console
        self.args = args
        self.kwargs = kwargs
        
    def receiver(self,):
        logger = logging.getLogger(name=self.name)
        logger.setLevel(self.logging_level)
        handler = HierarchicalTimedSizedRotatingHandler(*self.args, formatter=self.formatter, **self.kwargs)
        logger.addHandler(handler)
        
        if self.console:
            handlers = create_stream_handler(logging_level=self.logging_level, level_formats=self.level_formats, datefmt=self.datefmt)            
            for handler in handlers:
                logger.addHandler(handler)

        while True:
            record = self.logger_queue.get()
            if record:
                if record != LoggerQueueReceiver.ABORT:
                    local_logger(record, self.name)
                else:
                    self.logger_queue.close()
                    break
                
    def start(self):
        self.process = mp.Process(name='LoggerQueueReceiver', target=self.receiver, daemon=True)
        self.process.start()
    
    def stop(self):
        self.logger_queue.put(LoggerQueueReceiver.ABORT)
        self.process.join()
        
        
def local_logger(record, name=None):
    # if a name is specified, we use the named logger rather than the one
    # implied by the record.
    if name is None:
        name = record.name
        
    logger = logging.getLogger(name)
    # N.B. EVERY record gets logged. This is because Logger.handle
    # is normally called AFTER logger-level filtering. If you want
    # to do filtering, do it at the client end to save wasting
    # cycles and network bandwidth!
    logger.handle(record)


def get_log_record_tcp_request_handler(logger_queue=None, name=None):
    class LogRecordTCPRequestHandler(socketserver.BaseRequestHandler):
        """Handler for a streaming logging request.
    
        This basically logs the record using whatever logging policy is
        configured locally.
        """
            
        def handle(self):
            """Handles multiple requests - each expected to be a 4-byte length,
            followed by the LogRecord in pickle format. Logs the record
            according to whatever policy is configured locally.
            """
            #print('start reading from socket.')
            while True:
                chunk = self.request.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                chunk = self.request.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.request.recv(slen - len(chunk))
                obj = self.unPickle(chunk)
                record = logging.makeLogRecord(obj)
                #print('LogRecordStreamHandler handle:', record)
                self.handleLogRecord(record)
    
        def unPickle(self, data):
            return pickle.loads(data)
    
        def handleLogRecord(self, record):
            if logger_queue is None:
                # set name to None so record.name will be used
                local_logger(record, name=None)
            else:
                logger_queue.put(record)
                
    return LogRecordTCPRequestHandler        
        
class NwFilter(logging.Filter):
    """
    """
    def __init__(self, name, separator = '.', key='name', *args, **kwargs):
        super(NwFilter, self).__init__(*args, **kwargs)
        self.name = name
        self.separator = separator
        self.key = key
        self.__parts = name.split(separator)
        
    def filter(self, record):
        name = getattr(record, self.key)
        act = name.startswith(self.name)
        return act
    
    
def start_nwlogger(name=None, host=None, port=None, logging_level=None, formatter=None, level_formats=None, datefmt=None, console=False, started=None, abort=None, finished=None, args=(), kwargs={},):
    ''' starts logger for multiprocessing using queue.
     
    Returns:
         logger: set with correct socket handler
    '''
    # create console handler and set level to info
    
    logger = logging.getLogger(name=name)
    logger.setLevel(logging_level)
    logger.addFilter(LoggerAddHostFilter())
    
    if USE_QUEUE:
        logger_queue_receiver = LoggerQueueReceiver(name=name, logging_level=logging_level, formatter=formatter, level_formats=level_formats, datefmt=datefmt, console=console, args=args, kwargs=kwargs)
        logger_queue_receiver.start()
        logger_queue = logger_queue_receiver.logger_queue
    else:
        logger_queue = None
        handler = HierarchicalTimedSizedRotatingHandler(*args, formatter=formatter, **kwargs)
        logger.addHandler(handler)
        if console:
            handlers = create_stream_handler(logging_level=logging_level, level_formats=level_formats, datefmt=datefmt)            
            for handler in handlers:
                logger.addHandler(handler)       
            
    tcpserver = socketserver.ThreadingTCPServer((host, port), get_log_record_tcp_request_handler(logger_queue=logger_queue, name=name))
    tcpserver.allow_reuse_address = True
    tcpserverproc = th.Thread(name='ThreadingTCPServer', target=tcpserver.serve_forever, daemon=True)
    #print('About to start TCP server...', host, port)
    tcpserverproc.start()
    # notify caller, process started
    started.set()
    # wait for abort notification
    abort.wait()
    # abort received, shoutdown TCP server
    tcpserver.shutdown()
    tcpserver.server_close()
    tcpserverproc.join()
    if USE_QUEUE: 
        logger_queue_receiver.stop()
    finished.set()
    #print('finished start_nwlogger.')

class NwLogger(BaseLogger):
    def __init__(self, name=None, host='localhost', port=None, logging_level=logging.INFO, *args, **kwargs):    
        super(NwLogger, self).__init__(*args, name=name, logging_level=logging_level, **kwargs)
        
        self.host = host
        self.logger_initialized = False
        self.name = name if name is not None else 'nwlogger'
        self.logging_level = logging_level
        self.args = args
        #self.kwargs = kwargs
        
        if port is None:
            try:
                port = get_free_port()
            except Exception as e:
                raise AcrilogError('Failed to get free port.') from e
            if port is None:
                raise AcrilogError('Failed to get free port, got None.')
        #self.port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
        self.port = port
        
    def logger_info(self):
        info = super(NwLogger, self).logger_info()
        info.update({
                'host': self.host,
                'port': self.port,
               })
        return info

    @classmethod
    def get_logger(cls, logger_info, name= None):
        # create the logger to use.
        #logger = BaseLogger.get_logger(logger_info, name)
 
        try:
            name = name if name is not None else logger_info['name']
            # We don't really need host, since it is always localhost
            #host = logger_info['host']
            host = 'localhost'
            port = logger_info['port']
            #logging_level = logger_info['logging_level']
        except Exception as e:
            raise AcrilogError("Failed to get info from logger_info: {}".format(repr(logger_info))) from e
        
        #logger = logging.getLogger(name)
        #logger.setLevel(logging_level)
        logger = BaseLogger.get_logger(logger_info, name)
        
        # check logger has already proper handlers or not
        already_set = False
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.SocketHandler):
                already_set = already_set or (handler.port == port and handler.host == host)
                
        if not already_set:
            socketHandler = logging.handlers.SocketHandler(host, port)
            #print('get_logger adding handler pid:', os.getpid())
            # socket handler sends the event as an unformatted pickle
            logger.addHandler(socketHandler)
            logger.addFilter(LoggerAddHostFilter())
        return logger
    
    #def get_server_logger(self):
    #    return NwLogger.get_client_logger(self.logger_info())

    def start(self):
        self.started = mp.Event()
        self.abort = mp.Event()
        self.finished = mp.Event()
        
        start_nwlogger_kwargs = {
            'name': self.name, 
            'host': self.host, 
            'port': self.port, 
            'logging_level': self.logging_level, 
            'formatter': self.record_formatter, 
            'level_formats': self.level_formats, 
            'datefmt': self.datefmt, 
            'console': self.console,
            'started': self.started, 
            'abort': self.abort, 
            'finished': self.finished,     
            'args':self.handler_args, 
            'kwargs':self.handler_kwargs,
        }
        
        self.tcpserver = mp.Process(name='NwLogger', target=start_nwlogger, kwargs=start_nwlogger_kwargs, daemon=False)
        self.tcpserver.start()
        self.started.wait()
        #print('logger_proc event started received.')

        return 
    
    def stop(self,):
        if self.abort:
            #print('Stopping logger.')
            self.abort.set()
            #print('Joining tcpserver.')
            self.finished.wait()
            #self.started.clear(); self.finished.clear(); self.abort.clear()
            # TODO: need to work without explicitly calling terminate
            self.tcpserver.terminate()
            self.tcpserver.join()
            #print('Stopped logger.')
            
        