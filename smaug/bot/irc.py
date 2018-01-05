"""
Smaug IRC Interface
Provides a user interface from IRC thru private messages and a channel.

Some variable naming conventions:
    user: interal User object or ircuser
    nick: nickname
    nickhost: nick!user@host
    userhost: user@host

"""
from .log import IRCLogger
from .protocol import Protocol
from .command import *
from . import settings
import asyncio
import irc3

import logging
import collections
import time
import re
import random
from datetime import datetime

logger = logging.getLogger(__name__)


class Channel(object):

    def __init__(self, channelName, proto, logdir):
        self.channel = channelName
        self.log = IRCLogger(proto, logdir, channelName, channelName)
        self.names = {}

    def __repr__(self):
        return self.channel


class SmaugIRCFactory(object):

    def __init__(self, cmd, nick, password, server, port, channelNames, quitMessages, logdir):
        self.nick = nick 
        self.cmd = cmd
        self.password = password
        self.server = server
        self.port = port
        self.channelNames = channelNames
        self.quitMessages = quitMessages
        self.logdir = logdir

        config = dict(
            factory = self,
            nick = nick, 
            username = "smaug",
            realname = "Smaug Bot",
            autojoins = channelNames,
            autojoin_delay = 1,
            # on our server the actual max length seems to be 444
            max_length = 400, 
            host = server,
            port = port, 
            ssl = False,
            debug = True,
            verbose = True,
            raw = True,
            includes = [
                'irc3.plugins.core',
                'irc3.plugins.autojoins',
                'irc3.plugins.async',
                __name__,  # this register MyPlugin
            ]
        )
        self.bot = irc3.IrcBot.from_config(config)

    def startBot(self):
        """ Open a connection to the IRC server and begin running
            the async protocol.
        """
        logger.info("Connecting to the IRC server...")
        self.bot.create_connection()       


@irc3.plugin
class SmaugIRC(Protocol):

    proto = "irc"

    def __init__(self, bot):
        Protocol.__init__(self)
        self.bot = bot
        self.nick = bot.nick 
        self.factory = bot.config.factory
        self.cmd = self.factory.cmd
        self.channelNames = self.factory.channelNames
        self.kicked = False
        self.channels = {}
        # channel for private messages
        lnick = self.nick.lower()
        self.channels[lnick] = Channel(lnick, self, self.factory.logdir)
        for channelName in self.channelNames:
            self.channels[channelName] = Channel(channelName, self, self.factory.logdir)


    def getPublicChannelNames(self):
        return self.channelNames


    @irc3.event(irc3.rfc.CONNECTED)
    def on_connected(self, **kw):
        """ We are connected.. 
        """
        logger.info("Connection made.")
        self.cmd.registerProtocol(self)


    async def die(self):
        logger.info("Quitting IRC")
        messages = list(self.factory.quitMessages)
        random.shuffle(messages)
        # TODO: technically, quit should return a future so it could be awaited here
        self.factory.bot.quit(messages[0])
        # Wait for quit to be sent. This is very fragile... 
        await asyncio.sleep(1)
        self.connectionLost()


    def connectionLost(self):
        """ Connection to the server was lost.
        """
        for channel in self.channels:
            self.getLog(channel).disconnect()
            for name in self.channels[channel].names:
                nickhost = name +"!"+ self.channels[channel].names[name]
                user = self.getUser(nickhost)
                if user:
                    logger.info("Setting sign off for %s"%user)
                    user.profile.sign_off = datetime.now()
                    user.profile.save()
        self.close()


    def close(self):
        logger.info("Closing irc logs...")
        for channel in self.channels:
            self.channels[channel].log.closeLog()


    # IRC events dealing with the client

    @irc3.event(irc3.rfc.JOIN)
    async def on_join(self, mask, channel, **kwargs):
        """ Someone joined our channel.
        """
        if mask.nick == self.nick:
            await self.joined(channel)
        else:
            nickhost = str(mask)
            nick,userhost = nickhost.split("!",1)
            self.getLog(channel).join(nick, channel)
            await self.userWho(nickhost, channel)


    async def joined(self, channel):
        """ We have joined our channel.
        """
        self.getLog(channel).welcome(channel)
        if self.kicked:
            await self.sendMessage(channel, "Thanks asshole")   
            self.kicked = False

        c = CommandContext(self, channel, None, None, time.time())
        await self.cmd.notifyListeners(c, "joined", channel)
                
        # Issue a who command on the channel
        results = await self.bot.who(channel)
        if results['success']:
            for result in results['users']:
                nickhost = str(result['mask'])
                await self.userWho(nickhost, channel)
        else:
            logger.error("WHO command failed")


    async def userWho(self, nickhost, channel):
        """ When we join a channel we issue a WHO to log everyone in
            This command gets called once for every person we see
            when joining a channel
        """
        channel = channel.lower()
        nick,userhost = nickhost.split("!",1)
        logger.info("User who result for %s: %s" % (nick,userhost))
        self.channels[channel].names[nick] = userhost
        await self.userSeenEntering(nickhost, channel)


    @irc3.event(irc3.rfc.KICK)
    def on_kick(self, mask, channel, target, **kwargs):
        kickerNick,kickerUserhost = mask.split("!",1)
        message = kwargs['data']
        if target.nick == self.nick:
            self.kickedFrom(channel, kickerNick, message)
        else:
            self.userKicked(target, channel, kickerNick, message)


    def kickedFrom(self, channel, kicker, message):
        self.getLog(channel).kick(self.nick, kicker, message)
        self.kicked = True


    def userKicked(self, kickee, channel, kicker, message):
        channel = channel.lower()
        nick = kickee.split("!")[0]
        del self.channels[channel].names[nick]
        self.getLog(channel).kick(kickee, kicker, message)             
        #TODO: implement
        #self.whois(kickee).addCallback(self.processKick, channel, kickee, message)

    @irc3.event(irc3.rfc.PART)
    async def on_part(self, mask, channel, **kwargs):
        nickhost = str(mask)
        channel = channel.lower()
        nick = nickhost.split("!")[0]
        del self.channels[channel].names[nick]
        self.getLog(channel).part(nick, channel)
        await self.userSeenLeaving(nickhost, channel)
 

    @irc3.event(irc3.rfc.QUIT)
    async def on_quit(self, mask, data, **kwargs):
        nickhost = str(mask)
        message = data
        nick = nickhost.split("!")[0]
        channels = self.getUserChannels(nick)
        for channel in channels:
            if nick in self.channels[channel].names:
                del self.channels[channel].names[nick]
                self.getLog(channel).quit(nick, message)
            await self.userSeenLeaving(nickhost, channel, message)


    @irc3.event(irc3.rfc.NEW_NICK)
    async def on_new_nick(self, nick, new_nick, **kwargs):
        newnick = new_nick
        oldnickhost = str(nick)
        oldnick,host = oldnickhost.split("!",1)
        newnickhost = newnick+"!"+host
        channels = self.getUserChannels(oldnick)
        
        oldhandle = oldnick.split("|",1)
        newhandle = newnick.split("|",1)
        
        for channel in channels:
            del self.channels[channel].names[oldnick]
            self.channels[channel].names[newnick] = host
            self.getLog(channel).nick(oldnick, newnick)

            if oldhandle != newhandle:
                await self.userSeenLeaving(oldnickhost, channel)
                await self.userSeenEntering(newnickhost, channel)
 

    #TODO: implement
    async def processKick(self, whois, channel, kickee, message):
        """ We need the user@host of the kickee to auth them since
            it may be a user leaving
        """
        await self.userSeenLeaving(kickee+"!"+whois['userhost'], channel, message)
        return whois


    @irc3.event(irc3.rfc.TOPIC)
    @irc3.event(irc3.rfc.RPL_TOPIC)
    def on_topic(self, channel=None, data=None, **kwargs):
        """ Update the topic on join or on user action
        """
        if 'mask' in kwargs:
            who = kwargs['mask'].nick
        else:
            # In this case, kwargs looks like this: 
            # {'srv': 'tube.paranode.net', 'me': 'Smaug'}
            who = None
        self.getLog(channel).topic(data.rstrip(), who)


    @irc3.event(r"^:\S+ 333 \S+ (?P<channel>\S+).* (?P<nick>\S+) (?P<timestamp>\S+)")
    def on_topic_info(self, channel, nick, timestamp, **kwargs):
        """ Who set the topic and when?
            This is an extension to the RFC, so it's not part of irc3.
        """
        d = datetime.fromtimestamp(int(timestamp))
        self.getLog(channel).topicInfo(nick, d.strftime("%c"))
        

    @irc3.event(irc3.rfc.MODE)
    def on_mode(self, target, modes, data, **kwargs):
        """ Mode was changed 
        """
        nickhost = str(kwargs['mask'])
        channel = target
        mode = "%s %s" % (modes,data)
        self.getLog(channel).mode(nickhost.split("!")[0], mode)

    
    @irc3.event(irc3.rfc.PRIVMSG)
    async def on_privmsg(self, mask, target, data, event, **kwargs):
        nickhost = str(mask)
        if event=='PRIVMSG':
            if data.startswith("\x01ACTION "):
                # Strip off the "\01ACTION \01" wrapping
                await self.action(nickhost, target, data[8:-1])
            else:
                await self.privmsg(nickhost, target, data)
        elif event=='NOTICE':
            await self.notice(nickhost, target, data)
        else:
            logger.warn("Unrecognized message event: %s"%event) 
     

    async def action(self, nickhost, channel, data):
        self.getLog(channel).action(nickhost.split("!")[0], data)


    async def notice(self, nickhost, channel, message):
        """ Recieved a NOTICE, could be private or public
        """
        
        nick,userhost = nickhost.split("!",1)
        if channel == "AUTH" or channel == "irc": return
        channel = channel.lower()
        
        if channel == self.nick.lower():

            p = re.compile(r"(owned by someone else)|(This nickname is registered)")
            m = p.search(message)
            
            if nick == "NickServ" and m:
                await self.sendMessage("NickServ","identify %s" % self.factory.password)
            
            self.getLog(channel).privateNotice(nick,message)
        else:
            try:
                self.getLog(channel).publicNotice(nick,channel,message)
            except Exception as e:
                logger.exception("Error logging public notice for channel %s. Will log as private notice."%channel)
                # channel is probably something like $*.irc.host.net
                self.getLog(self.nick.lower()).privateNotice(nick,message)
            

    async def privmsg(self, nickhost, channel, message):
        """ Recieved a PRIVMSG, which is a misnomer. 
            It could be private or public, and it could be an action.
        """
        channel = channel.lower()
        if channel == self.nick.lower(): channel = ""
            
        nick = nickhost.split("!")[0]
        user = self.getUser(nickhost)

        authed = None
        if user:
            authed = self.authUserHost(user, nickhost)
            if not channel and not authed: # private message
                # attempt to reauth with password
                try:
                    passwd = message[message.rindex(" ")+1:]
                    authed = self.authUserPassword(user.id, nickhost, passwd)
                    if authed:
                        # it was a passwd, so remove it
                        message = message[:message.rindex(" ")]
                except ValueError:
                    pass # no password was given
        else:
            user = self.cmd.getAnonUser(nick)

        context = CommandContext(self, channel, user, nick, time.time())
        cmd,args = findCommand(message)
        
        # log this event
        if channel: # public message
            try:
                self.getLog(channel).publicMessage(nick,message)
            except:
                # channel is probably $*.fef.net
                self.getLog(self.nick.lower()).privateNotice(nick,message)
        else: # private message
            log_msg = message
            if args: log_msg = "!%s [arguments hidden]" % cmd
            self.getLog(self.nick.lower()).privateMessage(nick,log_msg)
        
        # execute command or process event
        if authed and cmd:
            error = await self.cmd.execute(cmd, context, args, authed=authed)
            for msg in error:
                await context.reply(msg)
        else:
            await self.cmd.notifyListeners(context, "hear", message)

        if authed and channel:
            user.profile.last_comment = datetime.now()
            user.profile.save()
 

    async def userSeenEntering(self, nickhost, channel, *message):
        """ This Smaug event happens when a user becomes known to us.
            This could happen thru a variety of ways, which are 
            protocol specific.
        """
        nick = nickhost.split("!")[0]
        user = self.getUser(nickhost) 
        if not user: return
        user.profile.sign_on = datetime.now()
        user.profile.save()
        c = CommandContext(self, channel, user, nick, time.time())
        if user == self.cmd.me:
            await self.cmd.notifyListeners(c, "enter", message)
        else:
            await self.cmd.notifyListeners(c, "hearEnter", message)


    async def userSeenLeaving(self, nickhost, channel, *message):
        """ This Smaug event happens when a user disappears for
            some reason.
        """
        nick = nickhost.split("!")[0]
        if not(self.wasLastAlias(nick, channel)): return
        user = self.getUser(nickhost) 
        if not user: return
        user.profile.sign_off = datetime.now()
        user.profile.save()
        c = CommandContext(self, channel, user, nick, time.time())
        if user == self.cmd.me:
            await self.cmd.notifyListeners(c, "exit", message)
        else:
            await self.cmd.notifyListeners(c, "hearExit", message)


    def getUser(self, nickhost):
        """ Given a nick or "nick!host" string, return the corresponding
            user id.
        """
        nick, userhost = nickhost.split("!", 1) 
        h = nick.split("|", 1)
        user = self.cmd.getUserByHandle(h[0])
        return user

 
    def authUserHost(self, user, nickhost):
        """ Given a user (nick!user@host) authenticate
            against the database. If the host is an ip and
            fails, then try to find the host (using reverse dns)
            and attempt to authenticate with that. This fixes a 
            an issue with IDENT not resolving the ip when a user connects.
        """
        nick, userhost = nickhost.split("!", 1) 
        username, host = userhost.split("@",1)
        success = self.cmd.authHost(user, userhost)
        
        if not success:
            p = re.compile(r"^[\.\d]+$")
            hostisip = p.match(host)
            if hostisip:
                try:
                    import socket
                    (hostname, aliaslist, ipaddrlist) = socket.gethostbyaddr(host)
                    success = self.cmd.authHost(user, "%s@%s"%(username,hostname))
                except Exception as e:
                    logger.exception("Error getting user hostname for IP="+host)
                    pass
            
        if success:
            logger.info("auth(host) %s",nickhost)
        else:
            logger.info("nonauth(host) %s",nickhost)

        return success

    
    def authUserPassword(self, user, nickhost, passwd):
        """ See authUser..
            This version uses a password instead of the host.
        """
        # TODO: reimplement this after reconciling BotUser and User
        return self.authUserHost(user, nickhost)

        #self.dbh = None
        #nick, userhost = nickhost.split("!", 1) 
        #h = nick.split("|", 1)
            
        #sql = """select handles.id
        #         from handles, users
        #         where handles.id = users.id
        #         and handles.handle = %s
        #         and users.passwd = password( %s )
        #      """
        
        #self.dbh.execute(sql,(h[0], passwd))
        #try:    
        #    id = self.dbh.fetchone()[0]
        #except:
        #    print "nonauth(passwd) %s" % nickhost
        #    return
 
        #print "auth(passwd) %s" % nickhost
        #return id


    async def sendNotification(self, where, content, em=None):
        """ Implements protocol
        """
        f = None
        if isinstance(content, str):
            f = await self.sendNotificationLine(where, content)
        elif isinstance(content, collections.Iterable):
            for line in content:
                f = await self.sendNotificationLine(where, line)
        else:
            raise Exception("Content is not string or iterable")
        return f

       
    async def sendNotificationLine(self, where, line):
        if where.startswith("#"):
            self.getLog(where).publicNotice(self.nick, where, line)
        else:
            self.getLog(self.nick.lower()).privateMessage(self.nick, line)
            
        self.bot.notice(where, line)


    async def sendMessage(self, where, content, em=None):
        """ Implements protocol
        """
        f = None
        if isinstance(content, str):
            f = await self.sendLine(where, content)
        elif isinstance(content, collections.Iterable):
            for line in content:
                f = await self.sendLine(where, line)
        else:
            raise Exception("Content is not string or iterable")
        return f
       

    async def sendLine(self, where, line):
        if where.startswith("#"):
            self.getLog(where).publicMessage(self.nick, line)
        else:
            self.getLog(self.nick.lower()).privateMessage(self.nick, line)

        # collapse adjacent end/start color tags
        line = re.sub(r"\x03(\s*?)\x03", "\x03", line)

        return self.bot.privmsg(where, line)


    # Commands

    @command("op")
    @level(10)
    @usage("!op [nick]")
    @desc("Set mode +o on nick. Defaults to caller.")
    async def modeOp(self, c, args):
        await self.setMode("+", c, args)


    @command("deop")
    @level(10)
    @usage("!deop [nick]")
    @desc("Set mode -o on nick. Defaults to caller (ha!).")
    async def modeDeop(self, c, args):
        await self.setMode("-", c, args)


    async def setMode(self, prefix, c, args):
        if not args: args = c.alias
        if c.channel:
            await self.bot.mode(c.channel, "%so %s"%(prefix,args))
        else:
            for channel in self.channels:
                await self.bot.mode(channel, "%so %s"%(prefix,args))


    @command("me")
    @level(20)
    @usage("!me <text>")
    @desc("Have me do something in the channel.")
    async def doAction(self, c, args):
        if not args: raise CmdParamError
        if c.channel:
            await self.bot.action(c.channel, args)
        else:
            for channel in self.channels:
                await self.bot.action(channel, args)


    @command("say")
    @level(20)
    @usage("!say <text>")
    @desc("Have me say something in the channel.")
    async def doSay(self, c, args):
        if not args: raise CmdParamError
        if c.channel:
            await self.bot.privmsg(c.channel, args)
        else:
            for channel in self.channels:
                await self.bot.privmsg(channel, args)


    @command("notice")
    @level(20)
    @usage("!notice <who> <text>")
    @desc("Have me beep someone.")
    async def doNotice(self, c, args):
        if not args: raise CmdParamError
        try:
            who,message = args.split(" ",1)
        except:
            raise CmdParamError
        await self.bot.notice(who, message)


    @command("version")
    @level(1)
    @usage("!version")
    @desc("Shows version and credits.")
    async def printVersion(self, c, args):
        botname = settings.BOT_NAME
        version = settings.VERSION
        author = settings.AUTHOR
        f = self.format
        out = u""
        out += f(u"«",color='white')
        out += f(u"«",color='lime')
        out += f(u"«",color='green')
        out += f(u" %s " % botname,color='lime')
        out += f(u"»",color='green')
        out += f(u"»",color='lime')
        out += f(u"» ",color='white')
        out += f(u"last",color='yellow')
        out += f(u"·",color='red')
        out += f(u"of",color='yellow')
        out += f(u"·",color='red')
        out += f(u"the",color='yellow')
        out += f(u"·",color='red')
        out += f(u"great",color='yellow')
        out += f(u"·",color='red')
        out += f(u"fire",color='yellow')
        out += f(u"·",color='red')
        out += f(u"drakes",color='yellow')
        out += f(u"·",color='red')
        out += f(u"°ver%s° [" % version,color='white')
        out += f(u"by %s" % author,color='green')
        out += f(u"]",color='white')
        await c.reply(out)


    # Utility methods


    def getChannel(self, channelName):
        lc = channelName.lower()
        if lc in self.channels:
            return self.channels[lc]
        raise Exception("No such channel: "+channelName)


    def getLog(self, channelName):
        return self.getChannel(channelName).log
 

    def getUserChannels(self, nick):
        """ Return a list of channels a user is on
        """ 
        channels = []
        for channelName in self.channels:
            for name in self.channels[channelName].names:
                if name == nick:
                    channels.append(channelName)
                    
        return channels


    def wasLastAlias(self, nick, channelName):
        """ Checks if this alias is the user's last
            in the specified channel
        """ 
        nh = nick.split("|",1)
        for name in self.channels[channelName].names:
            h = nick.split("|",1)
            if nh == h: return True
        
        return False


    def formatSender(self, nick):
        """ Implements protocol
        """
        return "<%s> " % nick

    
    def format(self, s, **attrib):
        """ Implements protocol
        """
        if not s: return None

        colorCodes = {
            'white'    : '00',
            'black'    : '01',
            'navy'     : '02',
            'green'    : '03',
            'red'      : '04',
            'maroon'   : '05',
            'purple'   : '06',
            'orange'   : '07',
            'yellow'   : '08',
            'lime'     : '09',
            'teal'     : '10',
            'aqua'     : '11',
            'blue'     : '12',
            'fuchsia'  : '13',
            'gray'     : '14',
            'silver'   : '15',
        }

        hexCodes = {
            'bold'     : 0x02,
            'color'    : 0x03,
            'reverse'  : 0x16,
            'underline': 0x1f,
        }

        for k in list(attrib.keys()):
            if k in hexCodes:
                code = chr(hexCodes[k])
                value = attrib[k]
                if value in colorCodes: value = colorCodes[value]
                s = code + str(value) + s + code

        return s


