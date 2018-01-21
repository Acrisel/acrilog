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
import logging
from acrilog.lib.sshlogger_pipe_handler import SSHLoggerPipeHandler

module_logger = logging.getLogger(__name__)


def main(*args, **kwargs):
    client = SSHLoggerPipeHandler(**kwargs)
    client.service_loop()


def cmdargs():
    import argparse

    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]

    parser = argparse.ArgumentParser(
        description="%s runs SSH logging Port Agent" % progname)
    parser.add_argument('--handler-id', type=str, dest="handler_id",
                        help="""Logger name.""")
    parser.add_argument('--log-info', type=str, dest='log_info',
                        help="""MpLogger info to using remote client.""")
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    # mp.freeze_support()
    # mp.set_start_method('spawn')

    args = cmdargs()
    main(**vars(args))
