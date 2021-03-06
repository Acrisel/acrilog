'''
Created on Sep 24, 2017

@author: arnon
'''
from acrilog import SSHLogger
import multiprocessing as mp
import logging


def log(logger_info):
    logger1 = SSHLogger.get_logger(logger_info, name='example.e1')
    logger2 = SSHLogger.get_logger(logger_info, name='example.e2')

    logger2.info('How quickly daft jumping zebras vex.')
    logger1.warning('Jail zesty vixen who grabbed pay from quack.')
    logger1.debug('Quick zephyrs blow, vexing daft Jim.')
    logger2.error('The five boxing wizards jump quickly.')


def main():

    sshlogger = SSHLogger('example', logging_level=logging.DEBUG, console=True, consolidate=True)
    sshlogger.start()

    logger_info = sshlogger.logger_info()
    logger = SSHLogger.get_logger(logger_info=logger_info)
    logger.info('Jackdaws love my big sphinx of quartz.')

    client = mp.Process(target=log, args=(logger_info,))
    client.start()
    client.join()

    sshlogger.stop()


if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    main()
