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

from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os

class TimedSizedRotatingHandler(TimedRotatingFileHandler, RotatingFileHandler):
    
    def __init__(self, filename, file_mode='a', maxBytes=0, backupCount=0, encoding='ascii', delay=False, when='h', interval=1, utc=False, atTime=None):
        """ 
        Combines RotatingFileHandler TimedRotatingFileHandler)  
        """
        
        if file_mode.startswith('w'):
            try: os.remove(filename)
            except: pass
        self.filename=filename
        RotatingFileHandler.__init__(self, filename=filename, mode=file_mode, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding, delay=delay)
        TimedRotatingFileHandler.__init__(self, filename=filename, when=when, interval=interval, backupCount=backupCount, encoding=encoding, delay=delay, utc=utc, atTime=atTime)
        
    def shouldRollover(self, record):
        """
        Check the need to rotate.     
        """
        timed_rollover=TimedRotatingFileHandler.shouldRollover(self, record) 
        sized_rollover=RotatingFileHandler.shouldRollover(self, record)
        
        return timed_rollover or sized_rollover

    def doRollover(self):
        """
        It is enough to use timed base rollover.
        """
        super(TimedRotatingFileHandler, self).doRollover()

    def getFilesToDelete(self):
        """
        It is enough to use timed base rollover.
        """
        return super(TimedRotatingFileHandler, self).getFilesToDelete()        
    
        
        
        