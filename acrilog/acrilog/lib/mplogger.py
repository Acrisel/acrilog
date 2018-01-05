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
import signal
from logging.handlers import QueueListener, QueueHandler
import multiprocessing as mp
from acrilog.lib.baselogger import BaseLogger, create_stream_handler, get_file_handler
# from acrilib import LoggerAddHostFilter
from acrilib import logging_record_add_host, HierarchicalTimedSizedRotatingHandler
# import threading as th


class _QueueListener(QueueListener):
    def __init__(self, started, *args, **kwargs):
        super(_QueueListener, self).__init__(*args, **kwargs)
        started.set()

    def dequeue(self, block,):
        ''' adding capture to EOF
        '''
        try:
            item = self.queue.get(block)
        except EOFError:
            item = None
        return item


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
        self.process_key = process_key
        self.logdir = logdir
        self.formatter = formatter
        self.name = name
        self.kwargs = kwargs

        key_handlers = dict([(p, dict()) for p in process_key])

        self.key_handlers = key_handlers
        self.global_handlers = global_handlers
        self.console_handlers = list()
        self.logging_level = logging_level

    def handle(self, record):
        """ Override handle a record.
        This just loops through the handlers offering them the record
        to handle.
        Args:
            record: The record to handle.
        """

        # Find handlers that match process keys
        handlers = list()
        record_name = record.__dict__.get('name', None)
        for process_key in self.process_key:
            record_key = record.__dict__.get(process_key, None)
            # print('record_key[process_key]: %s[%s]' %(record_key, process_key))
            # print('record_key[processName]: %s' %(repr(record.__dict__)))
            if record_key: 
                process_handlers = self.key_handlers[process_key]
                key_handlers = process_handlers.get(record_key, [])

                # avoid getting dedicated handler in special case when in consolidated mode and record with 
                # name equal to the global one (QueueListiner name)
                need_handler = len(key_handlers) ==0 and (record_key != self.name or len(self.global_handlers) ==0)
                if need_handler:
                    name = record_name
                    # file_prefix=self.kwargs.get('file_prefix')
                    # if file_prefix is None: file_prefix=name
                    # print('file_prefix, record_key, record_name:', file_prefix, record_key, record_name)
                    if record_name != record_key:
                        name = "%s.%s" % (name, record_key)
                    key_handlers = get_file_handler(logging_level=self.logging_level, logdir=self.logdir, process_key=name, formatter=self.formatter, **self.kwargs)
                    process_handlers[record_key] = key_handlers
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


def _start(name=None, loggerq=None, handlers=[], logging_level=None,
           formatter=None, level_formats=None, datefmt=None,
           console=False, started=None, abort=None, finished=None,
           verbose=False,
           args=(), kwargs={},):
    logger = logging.getLogger(name)
    logger.setLevel(logging_level)
    logging_record_add_host()
    # logger.addFilter(LoggerAddHostFilter())

    handlers += [HierarchicalTimedSizedRotatingHandler(
        *args, formatter=formatter, **kwargs)]

    if console:
        console_handlers = \
            create_stream_handler(logging_level=logging_level,
                                  level_formats=level_formats, datefmt=datefmt)
        handlers.extend(console_handlers)

    for handler in handlers:
        logger.addHandler(handler)

    queue_listener = _QueueListener(started, loggerq, *handlers)

    # queue_listener = LogRecordQueueListener(loggerq, verbose=verbose)
    if verbose:
        print('start_mplogger: starting listener.')
    queue_listener.start()
    # started.set()
    if verbose:
        print('start_mplogger: listener started.')
    # return queue_listener

    def exit_gracefully(signo, stack_frame, *args, **kwargs):
        queue_listener.stop()
        finished.set()

    # set exits
    signal.signal(signal.SIGHUP, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    # waiting on abort prevents creates a deadlock
    # looging shutdown therefore will not be called automatically.
    # therefore, shutdown needs to be explicit.
    abort.wait()
    queue_listener.stop()
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

        self._queue_listener = None
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
        # logger.addFilter(LoggerAddHostFilter())
        logging_record_add_host()
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

        # self._manager = manager = mp.Manager()
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

        #self._queue_listener = _start(**start_kwargs)

        self._queue_listener = \
            mp.Process(target=_start, kwargs=start_kwargs, daemon=True)
        # self._queue_listener = th.Thread(target=start_mplogger,
        #                               kwargs=start_kwargs, daemon=False)
        self._queue_listener.start()

        started.wait()

        logger_info = self.logger_info()
        logger = MpLogger.get_logger(logger_info=logger_info, name=name)
        return logger

    def __exit__(self):
        self.__del__()

    def __del__(self):
        self.stop()

    def stop(self,):
        # self._queue_listener.join()
        # return
        if self.verbose:
            print('mplogger stopping.')
        if self._queue_listener:
            if self.verbose:
                print('mplogger stop: stopping queue listener.')
            if self.abort:
                if self.verbose:
                    print('mplogger stop: setting abort.')
                self.abort.set()
                # self._queue_listener.stop()
                if self.verbose:
                    print('mplogger stop: waiting to finish.')
                self.finished.wait()
                if self.verbose:
                    print('mplogger stop: joining process.')
                self._queue_listener.join()


if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
