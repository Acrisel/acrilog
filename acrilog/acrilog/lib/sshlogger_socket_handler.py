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
import os
import sshutil
import logging
from copy import deepcopy
from acrilib import LoggerAddHostFilter
from acrilog import MpLogger, SSHLogger
import yaml
from sshutil import SSHPipeHandler


module_logger = logging.getLogger(__name__)


class SSHLoggerHandlerError(Exception):
    pass


class LoggingSSHPipeHandler(SSHPipeHandler):

    def __init__(self, log_info=None, *args, **kwargs):
        super(LoggingSSHPipeHandler, self).__init__(*args, **kwargs)
        try:
            log_info = yaml.load(log_info)
        except Exception as e:
            raise Exception("Failed to YAML.load('{}')".format(log_info)) from e
        
        # TODO: why do we need to do such assignment if logger has proper handler
        module_logger = self.module_logger
        module_logger.debug('Accepted logging info:{}.'.format(log_info))
        self.sshlogger = SSHLogger.get_logger(log_info)

    def handle(self, received):
        # it may be "TERM" message or alike
        if isinstance(received, logging.LogRecord):
            self.sshlogger.handle(received)


class SSHLoggerClientHandler(logging.Handler):
    ''' Logging handler to send logging records to remote logging server via SSHPipe

    NwLoggerClientHandler create handler object that sends 
    '''

    def __init__(self, logger_info, ssh_host,): # logger=None, logdir='/tmp'):
        ''' Initiate logger client on remote connecting to host:port

        Args:
            logger_info: result of SSHLogger.logger_info().
            ssh_host: SSH config Host to connect to.
        '''
        global module_logger
        super(SSHLoggerClientHandler, self).__init__()
        self.logger_info = logger_info
        self.sshpipe = None

        mp_logger_params = deepcopy(logger_info)
        del mp_logger_params['port']
        mp_logger_params['name'] += '_sshlogger_client_handler'
        handler_kwargs = mp_logger_params.get('handler_kwargs', dict())
        kwargs = {}
        kwargs.update(mp_logger_params)
        kwargs.update(handler_kwargs)
        
        self.mp_logger = MpLogger(**kwargs)
        self.mp_logger.start()
        mp_logger_info = self.mp_logger.logger_info()
        module_logger = MpLogger.get_logger(mp_logger_info, ) # name=mp_logger_params['name'])

        self.addFilter(LoggerAddHostFilter())

        # there is no need to pass loggerq via ssh.  
        # alos, it wont work anyhow.
        # but it does need port
        del mp_logger_info['loggerq']
        mp_logger_info['port'] = logger_info['port']
        # mp_logger_info['console'] = False

        command = ["{}".format(os.path.basename(__file__)), ]
        # server_host = logger_info['server_host']

        # logger_name = "{}_nwlogger_handler_{}_{}".format(logger_info['name'], logger_info['server_host'], os.getpid())
        logger_name = logger_info['name']
        kwargs = {"--handler-id": logger_name,
                  # "--host": server_host, #logger_info['host'],
                  # "--port": logger_info['port'],
                  '--log-info': '"{}"'.format(yaml.dump(mp_logger_info)),
                  # "--logging-level": logger_info['logging_level'],
                  # "--server-host": logger_info['server_host'],
                  # "--logdir": logdir,
                  }
        command.extend(["{} {}".format(name, value) for name, value in kwargs.items()])
        command = ' '.join(command)

        logname = '{}.sshpipe'.format(logger_info['name'],)

        try:
            self.sshpipe = sshutil.SSHPipe(ssh_host, command, name=logname, logger=module_logger) 
            module_logger.debug("Starting remote logger SSHPipe on host: {}, command: {}".format(ssh_host, command))
            self.sshpipe.start()
        except Exception as e:
            module_logger.exception(e)
            module_logger.critical('Agent failed to start: {}'.format(ssh_host,))
            response = self.sshpipe.response()
            raise SSHLoggerHandlerError("Failed to start SSHPipe to: {}; response: {}.".format(ssh_host, response)) 

        if not self.sshpipe.is_alive():
            module_logger.critical('Agent process terminated unexpectedly: {}'.format(ssh_host,))
            self.sshpipe.join()
            response = self.sshpipe.response()
            raise SSHLoggerHandlerError("Failed to start SSHPipe to: {}; response: {}.".format(ssh_host, response)) 

        module_logger.debug("Remote logger SSHPipe started.")

    def emit(self, record):
        try:
            self.sshpipe.send(record)
        except Exception as e:
            raise SSHLoggerHandlerError("Failed SSHPipe send: {}.".format(record.msg)) from e

    def __del__(self):
        self.close()

    def close(self):
        if self.mp_logger:
            self.mp_logger.stop()
        #if self.sshpipe:
        if self.sshpipe.is_alive():
            self.sshpipe.close()
        super(SSHLoggerClientHandler, self).close()

