"""
Chat logging to files and a database. 
Log files generally follow the MIRC log format for portability purposes. 
"""

from . import settings
from ..ircview import models

import time
import logging
from datetime import datetime
from os import makedirs
from os.path import exists

logger = logging.getLogger(__name__)


def currentTime():
    """ returns the current date and time in string format """
    curr_time = time.localtime(time.time())
    return time.strftime("%c",curr_time)


class Logger(object):
    """ general logging interface """

    def __init__(self, protocol, logdir, logname, channelName):
        self.protocol = protocol
        self.logdir = logdir
        self.logname = logname
        self.channelName = channelName
        self.fh = None
        self.month = 0
        self.checkMonth()


    def openLog(self,filename):
        if self.logdir:
            if not(exists(self.logdir)):
                makedirs(self.logdir)
            filename = self.logdir + "/" + filename
        self.fh = open(filename,"a")
        self.fh.write("\nSession Start: " + currentTime() + "\n")


    def closeLog(self):
        if self.fh:
            self.fh.write("\nSession End: " + currentTime() + "\n")
            self.fh.close()
            self.fh = None


    def checkMonth(self):
        """ check what month it is and open the appropriate log 
            if it is not already open """
        
        curr_time = time.localtime(time.time())
        new_month = time.strftime("%m",curr_time)
        
        if self.month != new_month:
            self.month = new_month
            self.closeLog()
            filename = self.logname +"_"+ \
                time.strftime("%Y%m01",curr_time) + ".log"
            self.openLog(filename)


    def write(self,s):
        """ print a string to the current log file """
        self.checkMonth()
        if self.fh:
            self.fh.write(s)
            self.fh.flush()


    def log(self,s):
        """ print a timestamp and the given string to the log """
        now = time.time()
        timestamp = str(int(now))
        self.write("%s %s\n" % (timestamp, s))


    def _addLine(self,body,handle=None,user=None,external_id=None):
        """ add a new log line to the database """

        if self.channelName not in self.protocol.getPublicChannelNames():
            # Only public channels are logged to the database
            return

        stamp = datetime.now()
        logline = models.LogLine(proto=self.protocol.proto,
                stamp=stamp,
                handle=handle,
                body=body,
                user=user,
                year=stamp.year,
                month=stamp.month,
                external_id=external_id,
                edited='N')
        logline.save()


    def logLine(self,s,body=None,handle=None,user=None,external_id=None):
        try:
            self.log(s)
            self._addLine(body or s,
                    handle=handle,
                    user=user,
                    external_id=external_id)
        except:
            logger.exception("Error logging line")



class IRCLogger(Logger):
    """ 
    A logger for irc clients 
    Conforms to the Mirc log format
    """

    def __init__(self,proto,logdir,logname,channelName):
        Logger.__init__(self,proto,logdir,logname,channelName)
        self.month = 0
        self.checkMonth()

    def log(self,s,body=None,handle=None,user=None,external_id=None):
        try:
            Logger.log(self, s)
            Logger._addLine(self, 
                    body or s,
                    handle=handle,
                    user=user,
                    external_id=external_id)
        except:
            logger.exception("Error logging to IRC log")


    def welcome(self, channel):
        self.log("*** Now talking in " + channel)

    def nick(self, oldNick, newNick):
        self.log("*** %s is now known as %s" % (oldNick,newNick))

    def action(self, nick, action):
        self.log("* %s %s" % (nick,action))

    def join(self, nick, channel):
        self.log("*** %s has joined %s" % (nick,channel))

    def part(self, nick, channel):
        self.log("*** %s has left %s" % (nick, channel))

    def kick(self, kicked, kicker, reason):
        self.log("*** %s was kicked by %s (%s)" % (kicked, kicker, reason))

    def quit(self, nick, message):
        self.log("*** %s has quit IRC (%s)" % (nick, message))

    def disconnect(self):
        self.log("*** Disconnected")

    def topic(self, topic, nick):
        if nick:
            self.log("*** %s changes topic to '%s'" % (nick, topic))
        else:
            self.log("*** Topic is '%s'" % topic)

    def topicInfo(self, nick, dateStr):
        self.log("*** Set by %s on %s" % (nick,dateStr))
        
    def mode(self, nick, mode):
        self.log("*** %s sets mode: %s" % (nick, mode)) 
        
    def publicNotice(self, nick, channel, notice):
        if nick=='Global': return
        self.log("-%s:%s- %s" % (nick, channel, notice))

    def privateNotice(self, nick, notice):
        if nick=='Global': return
        self.log("-%s- %s" % (nick, notice))
    
    def publicMessage(self, nick, message):
        self.log("<%s> %s" % (nick, message), body=message, handle=nick)

    def privateMessage(self, nick, message):
        self.log("<%s> %s" % (nick, message), body=message, handle=nick)
  
  
class DiscordLogger(Logger):
    """ 
    A logger for discord clients 
    Conforms to the Mirc log format
    """

    def __init__(self,proto,logdir,logname,channelName):
        Logger.__init__(self,proto,logdir,logname,channelName)


    def editLine(self,body,external_id):
        try:
            # get message history
            lines = models.LogLine.objects.filter(external_id__exact=external_id)
            # log to file
            self.log("(Edit Previous) %s" % body)

            # mark the last version of the LogLine as edited
            lastLine = list(lines)[-1]
            lastLine.edited = 'Y'
            lastLine.save()

            # add a new LogLine for the edit
            self._addLine(body,
                    handle=lastLine.handle,
                    user=lastLine.user,
                    external_id=external_id)

        except:
            logger.exception("Error editing Discord log")

    
    def deleteLine(self,external_id):
        try:
            # get message history
            lines = models.LogLine.objects.filter(external_id__exact=external_id)
            # mark all versions as deleted
            for line in lines:
                line.deleted = 'Y'
                line.save()

        except:
            logger.exception("Error deleting line from Discord log")


    def welcome(self, channel):
        self.logLine("*** Now talking in " + channel)

    def disconnect(self):
        self.logLine("*** Disconnected")

    def online(self, user, nick):
        self.logLine("*** %s has come online" % nick, user=user)

    def offline(self, user, nick):
        self.logLine("*** %s has gone offline" % nick, user=user)

    def nick(self, user, oldNick, newNick):
        self.logLine("*** %s is now known as %s" % (oldNick,newNick), user=user)

    def topic(self, topic):
        self.logLine("*** Topic is '%s'" % topic)

    def topicChanged(self, topic):
        self.logLine("*** Topic is now '%s'" % topic)

    def publicMessage(self, user, nick, message, external_id):
        s = "<%s> %s" % (nick, message)
        self.logLine(s,
                body=message,
                handle=nick,
                user=user,
                external_id=external_id)

    def privateMessage(self, user, nick, message, external_id):
        s = "<%s> %s" % (nick, message)
        self.log(s) # private messages are not saved in the database



