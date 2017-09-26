'''
Created on Sep 21, 2017

@author: arnon
'''
import logging
from copy import copy
from datetime import datetime

class MicrosecondsDatetimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        
        if ct is  None:
            ct=datetime.now()
            
        if datefmt is not None:
            s = ct.strftime(datefmt)
        else:
            #print('MicrosecondsDatetimeFormatter:', repr(ct),)
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
            
        return s

class LevelBasedFormatter(logging.Formatter):
    
    defaults={
        logging.DEBUG : u"%(asctime)-15s: %(process)-7s: %(levelname)-7s: %(message)s: %(module)s.%(funcName)s(%(lineno)d)",
        'default' : u"%(asctime)-15s: %(process)-7s: %(levelname)-7s: %(message)s",
        }
 
    def __init__(self, level_formats={}, datefmt=None):
        super(LevelBasedFormatter, self).__init__()
        formats = LevelBasedFormatter.defaults
        if level_formats:
            formats = copy(LevelBasedFormatter.defaults)
            formats.update(level_formats)
            
        self.datefmt = datefmt  
        self.formats = dict([(level, MicrosecondsDatetimeFormatter(fmt=fmt, datefmt=self.datefmt)) for level, fmt in formats.items()])
        self.default_format = self.formats['default']  
        logging.Formatter.__init__(self,) # fmt=self.default_format, datefmt=self.datefmt)

    def format(self, record):
        formatter = self.formats.get(record.levelno, self.default_format,)
        #print('LevelBasedFormatter:', formatter)
        result = formatter.format(record)
        return result
