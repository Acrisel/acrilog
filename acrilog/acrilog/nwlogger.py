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
import select
import multiprocessing as mp
import threading as th
from acrilog.baselogger import BaseLogger, get_file_handler, create_stream_handler
from acrilog.utils import get_free_port
from acrilog.timed_sized_logging_handler import HierarchicalTimedSizedRotatingHandler

class AcrilogError(Exception):
    pass

class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """
        
    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        #print('start reading from socket.')
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                return
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)
            #print('LogRecordStreamHandler handle:', record)
            self.handleLogRecord(record)

    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)
        

class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = True

    def __init__(self, host='localhost',
        port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        handler=LogRecordStreamHandler):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self, abort):
        while not abort.value:
            #rd, wr, ex = select.select([self.socket.fileno()],
            rd, wr, ex = select.select([self.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
        self.server_close()
        print('aborted serve_until_stopped.')
       

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
    
def start_nwlogger(name=None, host=None, port=None, logging_level=None, formatter=None, level_formats=None, datefmt=None, console=False, started=None, abort=None, args=(), kwargs={},):
    ''' starts logger for multiprocessing using queue.
     
    Returns:
         logger: set with correct socket handler
    '''
    # create console handler and set level to info
    
    #if MpLogger.logger_initialized:
    #if self.logger_initialized:
    #    return
    #self.logger_initialized = True
    
    #logger = logging.getLogger(name=self.logging_root)
    logger = logging.getLogger(name=name)
    logger.setLevel(logging_level)
    
    handler = HierarchicalTimedSizedRotatingHandler(*args, formatter=formatter, **kwargs)
    logger.addHandler(handler)
    if console:
        handlers = create_stream_handler(logging_level=logging_level, level_formats=level_formats, datefmt=datefmt)            
        for handler in handlers:
            logger.addHandler(handler)
    
    
    tcpserver = LogRecordSocketReceiver(host=host, port=port,)
    #print('About to start TCP server...', self.host, self.port)
    started.set()
    tcpserver.serve_until_stopped(abort)
    #print('shutting down tcp server.')
    #tcpserver.shutdown()
    print('finished start_nwlogger.')
    return 

class NwLogger(BaseLogger):
    def __init__(self, name='nwlogger', host='localhost', port=None, logging_level=logging.INFO, *args, **kwargs):    
        super(NwLogger, self).__init__(*args, name=name, logging_level=logging_level, **kwargs)
        
        self.host = host
        self.logger_initialized = False
        self.name = name 
        self.logging_level = logging_level
        #self.controller = None
        self.abort = None
        self.args = args
        self.kwargs = kwargs
        
        
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
 
        name = name if name is not None else logger_info['name']
        host = logger_info['host']
        port = logger_info['port']
        logging_level = logger_info['logging_level']
        logger = logging.getLogger(name)
        logger.setLevel(logging_level)
        socketHandler = logging.handlers.SocketHandler(host, port)
        # socket handler sends the event as an unformatted pickle
        logger.addHandler(socketHandler)

        return logger
    
    #def get_server_logger(self):
    #    return NwLogger.get_client_logger(self.logger_info())

    def start(self):
        #self.manager = mp.Manager()
        #self.controller = self.manager.Namespace()
        self.abort = mp.Value('i', 0)
        started = mp.Event()
        
        start_nwlogger_kwargs={
            'name':self.name, 
            'host':self.host, 
            'port':self.port, 
            'logging_level':self.logging_level, 
            'formatter':self.record_formatter, 
            'level_formats':self.level_formats, 
            'datefmt':self.datefmt, 
            'console':self.console,
            'started':started, 
            'abort':self.abort, 
            'args':self.args, 
            'kwargs':self.kwargs,
            }
        self.logger_proc = mp.Process(target=start_nwlogger, kwargs=start_nwlogger_kwargs, daemon=True)
        self.logger_proc.start()
        
        #self.tcpserver = start_nwlogger(**start_nwlogger_kwargs)
        
        started.wait()
        #print('logger_proc event started received.')

        return 
    
    def stop(self,):
        if self.abort:
            self.abort.value = 1
            if self.logger_proc.is_alive():
                print('Joining logger.')
                self.logger_proc.join()
        print('Stopped logger.')
 
