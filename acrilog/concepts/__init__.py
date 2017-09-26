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
from acrilog.utils import get_free_port
from acrilog.timed_sized_logging_handler import HierarchicalTimedSizedRotatingHandler


class AcrilogError(Exception):
    pass
        
        
class LogRecordTCPRequestHandler(socketserver.BaseRequestHandler):
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
        logger = logging.getLogger(record.name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)        
        
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
    
    logger_queue = None
    handler = HierarchicalTimedSizedRotatingHandler(*args, formatter=formatter, **kwargs)
    logger.addHandler(handler)
    if console:
        handlers = create_stream_handler(logging_level=logging_level, level_formats=level_formats, datefmt=datefmt)            
        for handler in handlers:
            logger.addHandler(handler)       
            
    tcpserver = socketserver.ThreadingTCPServer((host, port), LogRecordTCPRequestHandler)
    tcpserver.allow_reuse_address = True
    tcpserverproc = th.Thread(name='ThreadingTCPServer', target=tcpserver.serve_forever, daemon=True)
    tcpserverproc.start()
    # notify caller, process started
    started.set()
    # wait for abort notification
    abort.wait()
    # abort received, shoutdown TCP server
    tcpserver.shutdown()
    tcpserver.server_close()
    tcpserverproc.join()
    finished.set()
    #print('finished start_nwlogger.')

class NwLogger(BaseLogger):
    def __init__(self, name='nwlogger', host='localhost', port=None, logging_level=logging.INFO, *args, **kwargs):    
        super(NwLogger, self).__init__(*args, name=name, logging_level=logging_level, **kwargs)
        
        self.host = host
        self.logger_initialized = False
        self.name = name 
        self.logging_level = logging_level
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
        #print('get_logger adding handler pid:', os.getpid())
        # socket handler sends the event as an unformatted pickle
        logger.addHandler(socketHandler)
        return logger
    
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
            'args': self.args, 
            'kwargs': self.kwargs,
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
            self.started.clear(); self.finished.clear(); self.abort.clear()
            # TODO: need to work without explicitly calling terminate
            self.tcpserver.terminate()
            self.tcpserver.join()
            #print('Stopped logger.')
 
def log(logger_info):
    logger1 = NwLogger.get_logger(logger_info, name='example.e1')
    logger2 = NwLogger.get_logger(logger_info, name='example.e2')
    
    logger2.info('How quickly daft jumping zebras vex.')
    logger1.warning('Jail zesty vixen who grabbed pay from quack.')
    logger1.debug('Quick zephyrs blow, vexing daft Jim.')
    logger2.error('The five boxing wizards jump quickly.')
           
                    
def main():
    
    nwlogger = NwLogger('example', logging_level=logging.DEBUG, consolidate=True)
    nwlogger.start()
    
    logger_info = nwlogger.logger_info()
    logger = NwLogger.get_logger(logger_info=logger_info)
    logger.info('Jackdaws love my big sphinx of quartz.')
        
    client = mp.Process(target=log, args=(logger_info,))
    client.start()
    client.join()
    
    nwlogger.stop()

    
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    main()
