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
from copy import deepcopy
from acrilog.utils import get_hostname, get_ip_address #, logger_process_lambda

module_logger = logging.getLogger(__name__)

def logger_process_lambda(logger_info):
    logger_info = deepcopy(logger_info)
    def internal(name=None):
        if name is not None:
            logger_info['name'] = name
        logger = NwLogger.get_logger(logger_info)
        return logger
    return internal

class NwLoggerHandlerError(Exception): pass

def start_nwlogger_client(**logger_info):
    logger = NwLogger.get_logger(logger_info)
    data_queue = mp.Queue()
    listener_started = mp.Event()
    
    kwargs = {
        'queue': data_queue,
        'started_event': listener_started,
        }
    
    listener = mp.Process(target=sshutil.pipe_listener_forever, kwargs=kwargs, daemon=False)
    listener.start()
    
    logger.debug('Waiting for Remote logger pipe listener to start.')
    listener_started.wait()
    logger.debug('Remote logger pipe listener started.')
    
    active = True
    while active:
        msg, error = data_queue.get()
        active = msg not in ['TREM', 'STOP', 'FINISH'] # msg == sshutil.EXIT_MESSAGE
        if active:
            logger.handler(msg)
            
    logger.debug('Remote logger pipe listener deactivated.')
 
class NwLoggerClientHandler(logging.Handler):
    ''' Logging handler to send logging records to remote logging server via SSHPipe
    
    NwLoggerClientHandler create handler object that sends 
    '''
    
    def __init__(self, logger_info, ssh_host, logger=None, logdir='/tmp'):
        ''' Initiate logger client on remote connecting to host:port
        
        Args:
            logger_info: result of NwLogger.logger_info().
            ssh_host: SSH config Host to connect to.
        '''
        super(NwLoggerClientHandler, self).__init__()
        self.logger_info = logger_info
        #self.local = local
        
        command = ["{}".format(os.path.basename(__file__)),]
        #server_host = logger_info['server_host']
        kwargs = {"--name": logger_info['name'],
                  #"--host": server_host, #logger_info['host'],
                  "--port": logger_info['port'],
                  "--logging-level": logger_info['logging_level'],
                  "--logdir": logdir,
                  }
        command.extend(["{} {}".format(name, value) for name, value in kwargs.items()])
        command = ' '.join(command)
        #print('running SSHPipe:', ssh_host, command)
        
        logname = '{}.sshpipe.log'.format(logger_info['name'])
        self.sshpipe = sshutil.SSHPipe(ssh_host, command, name=logname, logger=logger) # get_logger=logger_process_lambda(NwLogger, self.logger_info))
        self.logger = logger
        if logger:
            logger.debug("Starting remote logger SSHPipe on host: {}, command: {}".format(ssh_host, command))
        self.sshpipe.start()
        
        if logger:
            logger.debug("Remote logger SSHPipe started.")
            
    def __logger_process_lambda(self,):
        logger_info = deepcopy(self.logger_info)
        def internal(self, name=None):
            if name is not None:
                logger_info['name'] = name
            logger = NwLogger.get_logger(logger_info)
            return logger
        return internal
        
    def emit(self, record):
        #if not hasattr(record, 'host'):
        #    record.host = get_hostname()
        #    record.ip = get_ip_address()if logger:
        #logger = self.logger
        #if logger:
        #    logger.debug("Emitting logger record to pipe: {}".format(repr(record)))
        try:
            self.sshpipe.send(record)
        except Exception as e:
            raise NwLoggerHandlerError("Failed SSHPipe send: {}.".format(record.msg)) from e
        
def cmdargs():
    import argparse
    
    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]
    
    parser = argparse.ArgumentParser(description="%s runs SSH logging Port Agent" % progname)
    parser.add_argument('--name', type=str, 
                        help="""Logger name.""")
    #parser.add_argument('--host', type=str, 
    #                    help="""Host to forward messages to (localhost).""")
    parser.add_argument('--port', type=int, 
                        help="""Port to forward messages to.""")
    parser.add_argument('--logging-level', type=int, default=sshutil.EXIT_MESSAGE, dest='logging_level',
                        help="""string to use as exit message, default: {}.""".format(sshutil.EXIT_MESSAGE))
    parser.add_argument('--logdir', type=str, default='/tmp',
                        help="""Logdir to use, defaults to /tmp.""")
    args = parser.parse_args()  
    
    return args
 
        
if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    
    args = cmdargs()
    start_nwlogger_client(**vars(args))
