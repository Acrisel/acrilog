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
import logging
from acrilog import SSHLogger
import yaml
from sshpipe import SSHPipeHandler


mlogger = logging.getLogger(__name__)


class SSHLoggerPipeHandler(SSHPipeHandler):

    def __init__(self, log_info=None, *args, **kwargs):
        global mlogger
        super(SSHLoggerPipeHandler, self).__init__(*args, **kwargs)
        try:
            log_info = yaml.load(log_info)
        except Exception as e:
            msg = "Failed to YAML.load('{}')".format(log_info)
            raise RuntimeError(msg) from e

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
