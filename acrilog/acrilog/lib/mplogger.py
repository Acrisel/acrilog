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
from acrilog.lib.baselogger import BaseLogger, create_stream_handler
from acrilib import LoggerAddHostFilter, HierarchicalTimedSizedRotatingHandler


class LogRecordQueueListener(QueueListener):
    def __init__(self, queue, verbose=False):  # *handlers):
        super(LogRecordQueueListener, self).__init__(queue,)  # *handlers)
        self.verbose = verbose

    def handle(self, record):
        name = record.name
        logger = logging.getLogger(name)
        record = self.prepare(record)
        logger.handle(record)

    def start_server_wait_event(self, abort):
        if self.verbose:
            print('start_server_wait_event: starting.')
        self.start()
        if self.verbose:
            print('start_server_wait_event: waiting for abort.')
        abort.wait()
        if self.verbose:
            print('start_server_wait_event: stopping.')
        self.stop()


def start_mplogger(name=None, loggerq=None, handlers=[], logging_level=None,
                   formatter=None, level_formats=None, datefmt=None,
                   console=False, started=None, abort=None, finished=None,
                   verbose=False,
                   args=(), kwargs={},):
    logger = logging.getLogger()
    logger.setLevel(logging_level)
    logger.addFilter(LoggerAddHostFilter())

    handlers += [HierarchicalTimedSizedRotatingHandler(*args,
                                                       formatter=formatter,
                                                       **kwargs)]
    if console:
        console_handlers = create_stream_handler(logging_level=logging_level,
                                                 level_formats=level_formats,
                                                 datefmt=datefmt)
        handlers.extend(console_handlers)

    for handler in handlers:
        logger.addHandler(handler)

    queue_listener = LogRecordQueueListener(loggerq, verbose=verbose)
    if verbose:
        print('start_mplogger: setting started.')
    started.set()
    queue_listener.start_server_wait_event(abort)
    if verbose:
        print('start_mplogger: setting finished.')
    finished.set()


class MpLogger(BaseLogger):
    ''' Builds Multiprocessing logger such all process share the same
    logging mechanism
    '''

    def __init__(self, name=None, logging_level=logging.INFO, handlers=[],
                 verbose=False, *args, **kwargs):
        '''Initiates MpLogger service

        Args:
            name: base name to use for file logs.
            logdir: folder to which log files will be written; if not provided,
                log files will not be created logging_level: level from which
                logging will be done
            level_formats: mapping of logging levels to formats to use for
                constructing message
            datefmt: date format to use
            process_key: list of record names that would be used to create
                files
            console_name: when set, records assigned to process_key handler
                will also routed to global handlers.
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
        super(MpLogger, self).__init__(*args, name=name,
                                       logging_level=logging_level, **kwargs)

        self.queue_listener = None
        self.abort = None
        self.logger_initialized = False
        self.handlers = handlers
        self.verbose = verbose

    def logger_info(self):
        info = super(MpLogger, self).logger_info()
        info.update({
                'loggerq': self.loggerq,
               })
        return info

    @classmethod
    def get_logger(cls, logger_info, name=None):
        # create the logger to use.
        if name is not None:
            logger_info['name'] = name
        logger = BaseLogger.get_logger(logger_info)
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

    def start(self, name=None):
        ''' starts logger for multiprocessing using queue.

        Args:
            name: identify starting process to allow it log into its own
                logger.

        Returns:
            logger: set with correct Q handler.
        '''
        # create console handler and set level to info

        if self.logger_initialized:
            return
        self.logger_initialized = True

        self.loggerq = mp.Queue()

        self.abort = mp.Event()
        started = mp.Event()
        self.finished = mp.Event()

        start_kwargs = {
            'name': self.name,
            'loggerq': self.loggerq,
            'handlers': self.handlers,
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
            'verbose': self.verbose,
            }
        self.logger_proc = mp.Process(target=start_mplogger,
                                      kwargs=start_kwargs, daemon=True)
        self.logger_proc.start()

        started.wait()
        logger_info = self.logger_info()
        logger = MpLogger.get_logger(logger_info=logger_info, name=name)
        return logger

    def stop(self,):
        if self.abort:
            print('stop: setting abort.')
            self.abort.set()
            print('stop: waiting to finish.')
            self.finished.wait()
            print('stop: joining process.')
            self.logger_proc.join()


if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
