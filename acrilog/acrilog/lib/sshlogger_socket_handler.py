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
import os
import sshpipe as sp
import logging
from copy import deepcopy
from acrilib import logging_record_add_host  # LoggerAddHostFilter
from acrilog import MpLogger, SSHLogger
import yaml


mlogger = logging.getLogger(__name__)


class SSHLoggerHandlerError(Exception):
    pass


class LoggingSSHPipeHandler(sp.SSHPipeHandler):

    def __init__(self, log_info=None, *args, **kwargs):
        global mlogger
        super(LoggingSSHPipeHandler, self).__init__(*args, **kwargs)
        try:
            log_info = yaml.load(log_info)
        except Exception as e:
            msg = "Failed to YAML.load('{}')".format(log_info)
            raise Exception(msg) from e

        # TODO: why do we need to do such assignment
        #       if logger has proper handler
        mlogger = self.mlogger
        mlogger.debug('Accepted logging info:\n    {}.'.format(log_info))
        self.sshlogger = SSHLogger.get_logger(log_info)

    def handle(self, received):
        # it may be "TERM" message or alike
        mlogger.debug('Handling record:\n    {}.'
                            .format(repr(received)))
        if isinstance(received, logging.LogRecord):
            self.sshlogger.handle(received)


class SSHLoggerClientHandler(logging.Handler):
    ''' SSHPipe Logging handler to send logging records to remote logging server

    SSHLoggerClientHandler create handler object that sends
    '''

    def __init__(self, logger_info, ssh_host, verbose=False):
        ''' Initiate logger client on remote connecting to host:port

        Args:
            logger_info: result of SSHLogger.logger_info().
            ssh_host: SSH config Host to connect to.
        '''
        global mlogger
        super(SSHLoggerClientHandler, self).__init__()
        self.logger_info = logger_info
        self.sshpipe = None
        self.verbose = verbose

        mp_logger_params = deepcopy(logger_info)
        del mp_logger_params['port']
        name = mp_logger_params['name']
        handler_id = name + '_sshlogger_client_handler'
        mp_logger_params['name'] = handler_id
        # handler_id = mp_logger_params['name'] + '_sshlogger_socket_handler'
        handler_kwargs = mp_logger_params.get('handler_kwargs', dict())
        kwargs = {}
        kwargs.update(mp_logger_params)
        kwargs.update(handler_kwargs)

        self._mp_logger = MpLogger(**kwargs, verbose=self.verbose)
        self._mp_logger.start()
        mp_logger_info = self._mp_logger.logger_info()
        mlogger = MpLogger.get_logger(mp_logger_info, )

        logging_record_add_host()
        # self.addFilter(LoggerAddHostFilter())

        # there is no need to pass loggerq via ssh.
        # also, it wont work anyhow.
        # but it does need port
        del mp_logger_info['loggerq']
        mp_logger_info['port'] = logger_info['port']
        # mp_logger_info['console'] = False

        # this program has a twin in bin as executable
        command = ["{}".format(os.path.basename(__file__)), ]
        # server_host = logger_info['server_host']

        # logger_name = logger_info['name']
        kwargs = {"--handler-id": handler_id,  # logger_name,
                  # "--host": server_host, #logger_info['host'],
                  # "--port": logger_info['port'],
                  '--log-info': '"{}"'.format(yaml.dump(mp_logger_info)),
                  # "--logging-level": logger_info['logging_level'],
                  # "--server-host": logger_info['server_host'],
                  # "--logdir": logdir,
                  }
        command.extend(["{} {}".format(name, value)
                        for name, value in kwargs.items()])
        # command = ' '.join(command)

        logname = logger_info['name']

        try:
            # Important: cannot pass logger from here to SSHPipe
            # If logger is passed, infinite recursion is created.
            self.sshpipe = sp.SSHTunnel(ssh_host, command,
                                        name=logname, logger=mlogger)
            msg = "Starting remote logger SSHPipe on host: {}, command: {}"
            mlogger.debug(msg.format(ssh_host, command))
            self.sshpipe.start()
        except Exception as e:
            mlogger.exception(e)
            mlogger.critical(
                'Agent failed to start: {}'.format(ssh_host))
            response = self.sshpipe.response()
            raise SSHLoggerHandlerError(
                ("Failed to start SSHPipe to: {}; "
                 "response: {}.").format(ssh_host, response))

        if not self.sshpipe.is_alive():
            mlogger.critical('Agent process terminated unexpectedly: {}.'.format(ssh_host))
            self.sshpipe.join()
            response = self.sshpipe.response()
            raise SSHLoggerHandlerError(
                ("Failed to start SSHPipe to: {}; "
                 "response: {}.").format(ssh_host, response))

        if self.verbose:
            print("SSHLoggerClientHandler: Remote logger SSHPipe started.", self.sshpipe.is_alive())
        mlogger.debug("Remote logger SSHPipe started.")

    def emit(self, record):
        if self.verbose:
            print("SSHLoggerClientHandler: emitting record:", repr(record))
        try:
            self.sshpipe.send(record)
        except Exception as e:
            raise e
            raise SSHLoggerHandlerError(
                "Failed SSHPipe send: {}.".format(record.msg)) from e

    def __del__(self):
        if self._mp_logger:
            self.close()

    def close(self):
        if self.verbose:
            print("SSHLoggerClientHandler: closing handler.")
        if self._mp_logger:
            if self.verbose:
                print("SSHLoggerClientHandler: stopping mplogger.")
            self._mp_logger.stop()
            self._mp_logger = None
        if self.sshpipe.is_alive():
            if self.verbose:
                print("SSHLoggerClientHandler: closing sshpipe.")
            self.sshpipe.close()
        if self.verbose:
            print("SSHLoggerClientHandler: closing hanlers.")
        #super(SSHLoggerClientHandler, self).close()
