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

import time
import random
import logging
from acrilog import MpLogger
import multiprocessing as mp
import os


def procly(limit=1, logger_info=None):
    logger = MpLogger.get_logger(logger_info, name="%s.procly.%s"
                                 % (logger_info['name'], limit), )
    # logger=logging.getLogger("acrilog")
    # logger.setLevel(logging.DEBUG)

    for i in range(limit):
        sleep_time = 3 / random.randint(1, 10)
        logger.debug("%s/%s - sleep %4.4ssec starting"
                     % (i, limit, sleep_time))
        time.sleep(sleep_time)
        logger.info("%s/%s - sleep %4.4ssec completed"
                    % (i, limit, sleep_time))


level_formats = {
    logging.DEBUG: (u"[ %(asctime)-26s ][ %(processName)-11s ]"
                    "[ %(levelname)-7s ][ %(message)s ]"
                    "[ %(module)s.%(funcName)s(%(lineno)d) ]"),
    'default':   (u"[ %(asctime)-26s ][ %(processName)-11s ]"
                  "[ %(levelname)-7s ][ %(message)s ]"),
    }


if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')

    mplogger = MpLogger(
        name='acrilog',
        logdir='/var/acrisel/log/acrilog',
        logging_level=logging.DEBUG,
        level_formats=level_formats,
        encoding='utf8',
        console=True,
        # consolidate=True,
        datefmt='%Y-%m-%d,%H:%M:%S.%f',
        file_mode='w',
        file_prefix='acrilog_%s' % os.getpid(),
        file_suffix='%s' % os.getpid(),
        )
    mplogger.start()

    # logger=logging.getLogger('acrilog')
    logger_info = mplogger.logger_info()
    logger = MpLogger.get_logger(logger_info)
    # logger=MpLogger.get_logger(name='acrilog', logger_info=logger_info)
    # print('logger_info:', logger_info)
    logger.info("starting sub processes")
    procs = list()
    seq = 0
    for limit in range(3):
        seq += 1
        proc = mp.Process(target=procly, args=(limit+1, logger_info))
        proc.name = 'subproc-%s' % seq
        procs.append(proc)
        proc.start()
        logger.info("Sub process {} launched.".format(proc.name))

    for proc in procs:
        if proc:
            proc.join()

    logger.debug("sub processes completed; \u2754")
    logger.info("sub processes completed;")

    mplogger.stop()
