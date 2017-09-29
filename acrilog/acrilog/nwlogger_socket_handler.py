#!/usr/bin/env python

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
import multiprocessing as mp
from acrilog import NwLogger
import os
import sshutil
import logging

def start_nwlogger_client(**logger_info):
    logger = NwLogger.get_logger(logger_info)
    data_queue = mp.Queue()
    
    kwargs = {
        'queue': data_queue,
        }
    listener = mp.Process(target=sshutil.pipe_listener_forever, kwargs=kwargs, daemon=False)
    listener.start()
    
    active = True
    while active:
        msg, error = data_queue.get()
        active = sshutil.EXIT_MESSAGE
        if active:
            logger.handler(msg)
 
class NwLoggerClientHandler(logging.Handler):
    ''' Logging handler to send logging records to remote logging server via SSHPipe
    
    NwLoggerClientHandler create handler object that sends 
    '''
    def __init__(self, logger_info,):
        ''' Initiate logger client on remote connecting to host:port
        
        Args:
            logger_info: result of NwLogger.logger_info().
            local: indicates creation of local logs on remote host.
        '''
        self.logger_info = logger_info
        #self.local = local
        
        command = ["{}".format(__file__),]
        kwargs = {"--name": logger_info['name'],
                  "--host": logger_info['host'],
                  "--port": logger_info['port'],
                  "--logging-level": logger_info['logging_level'],
                  }
        command.append(["{} {}".format(name, value) for name, value in kwargs.items()])
        self.sshpipe = sshutil.SSHPipe(self.host, ' '.join(command))
        self.sshpipe.start()
        
        
    def emit(self, record):
        self.sshpipe.send(record)
        
def cmdargs():
    import argparse
    
    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]
    
    parser = argparse.ArgumentParser(description="%s runs SSH logging Port Agent" % progname)
    parser.add_argument('--name', type=str, 
                        help="""Logger name.""")
    parser.add_argument('--host', type=str, 
                        help="""Host to forward messages to (localhost).""")
    parser.add_argument('--port', type=int, 
                        help="""Port to forward messages to.""")
    parser.add_argument('--logging-level', type=int, default=sshutil.EXIT_MESSAGE, dest='logging_level',
                        help="""string to use as exit message, default: {}.""".format(sshutil.EXIT_MESSAGE))
    args = parser.parse_args()  
    
    return args
 
        
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    
    args = cmdargs()
    start_nwlogger_client(**args.vars())
