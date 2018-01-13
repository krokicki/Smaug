"""
Smaug Discord Interface
Provides a user interface through Discord.

Some variable naming conventions:
    user: internal User object
    channel: Discord Channel object
    channelName: Channel name prepended with hash, e.g. "#general"
    sc: SmaugChannel wrapper object

"""
import discord

from .log import DiscordLogger
from .protocol import Protocol
from .command import *
from . import settings
from smaug.utils import dates

import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

def getChannelName(channel):
    if not channel: return None
    if channel.is_private:
        # TODO: support group channels
        if channel.owner:
            return channel.owner.name
        else:
            return channel.recipients[0].name
    return "#"+channel.name


class SmaugChannel(object):

    def __init__(self, channel, proto, logdir):
        self.channel = channel
        if channel:
            logname = "%s_%s" % (channel.server.name, channel.name)
            self.name = getChannelName(channel)
        else:
            logname = "private_messages"
            self.name = None
        self.log = DiscordLogger(proto, logdir, logname, self.name)
        self.names = {}

    def __repr__(self):
        return self.name


class SmaugDiscord(discord.Client, Protocol):

    proto = "discord"

    def __init__(self, cmd, token, channelNames, logdir):
        Protocol.__init__(self)
        discord.Client.__init__(self)
        self.cmd = cmd
        self.token = token
        self.channelNames = channelNames
        self.logdir = logdir
        self.private_channel = None
        self.channels = None
        self.ready = False
        self.gameStartTimes = {}


    def getPublicChannelNames(self):
        return self.channelNames


    def runBot(self):
        """ Runs the bot event loop. Does not return.
        """
        logger.info("Connecting to Discord server...")
        self.run(self.token)


    def startBot(self):
        """ Begins and returns the bot event loop.
        """
        logger.info("Connecting to Discord server...")
        return self.start(self.token)
 
    
    def connectionLost(self, reason):
        """ Connection to the server was lost.
        """
        if self.channels:
            for channel in self.channels:
                self.getLog(channel).disconnect()
                sc = self.getChannel(channel)
                for name in sc.names:
                    nickhost = name +"!"+ sc.names[name]
                    if nickhost:
                        user = self.getUser(nickhost)
                        if user:
                            user.profile.sign_off = datetime.now()
                            user.profile.save()

    
    # Event handlers

    async def on_ready(self):
        
        if self.ready: return

        self.cmd.registerProtocol(self)

        self.private_channel = SmaugChannel(None, self, self.logdir)
        self.channels = {}
        for channel in self.get_all_channels():
            if channel.type==discord.ChannelType.text:
                channelName = getChannelName(channel)
                if channelName in self.channelNames:
                    logger.info("Registering channel '%s' (id=%s)" % (channel.name, channel.id))
                    sc = SmaugChannel(channel, self, self.logdir)
                    self.channels[sc.name] = sc
                    await self.joined(channel)
        
        logger.info("Discord client is now ready")
        self.ready = True


    async def joined(self, channel):
        self.getLog(channel).welcome(channel.name)
        self.getLog(channel).topic(channel.topic.rstrip())
        c = CommandContext(self, getChannelName(channel), None, None, time.time())
        await self.cmd.notifyListeners(c, "joined", channel.name)
        for member in self.get_all_members():
            await self.userSeenEntering(member, None)


    async def on_resumed(self):
        logger.info("Resumed")


    async def on_member_update(self, before, after):

        logger.info("Member update for %s"%after)

        if before.status==discord.Status.offline and after.status==discord.Status.online:
            for sc in self.channels.values():
                await self.userSeenEntering(after, sc.channel)

        elif before.status==discord.Status.online and after.status==discord.Status.offline:
            for sc in self.channels.values():
                await self.userSeenLeaving(after, sc.channel)

        if before.nick != after.nick:
            for sc in self.channels.values():
                user = self.getUser(self.getHandle(after))
                beforeNick = self.getNick(before)
                afterNick = self.getNick(after)
                self.getLog(sc.channel).nick(user, beforeNick, afterNick)
        
        if before.game != after.game:
            nick = self.getNick(after)
            s = None

            content = []

            if before.game:
                game = before.game

                delta = ""
                if nick in self.gameStartTimes:
                    elapsed = time.time() - self.gameStartTimes[nick]
                    del self.gameStartTimes[nick]
                    delta = " for %s"%dates.pretty_time_delta(elapsed)
                    action = "streamed" if game.type==1 else "played"
                    content.append(":stop_button: %s %s %s%s" % (nick, action, game.name, delta))
                else:
                    action = "streaming" if game.type==1 else "playing"
                    content.append(":stop_button: %s has stopped %s %s" % (nick, action, game.name))

            if after.game:
                game = after.game
                self.gameStartTimes[nick] = time.time()
                if game.type==1:
                    action = "streaming"
                    suffix = ": %s" % game.url
                else:
                    action = "playing"
                    suffix = ""
                content.append(":arrow_forward: %s is now %s %s%s" % (nick, action, game.name, suffix))

            if content:
                for channel in self.channels:
                    # We have to send each line individually so 
                    # that they line up correctly
                    for line in content:
                        await self.sendMessage(channel, line)


    async def userSeenEntering(self, discordUser, channel, *message):
        """ This Smaug event happens when a user becomes known to us.
            This could happen thru a variety of ways, which are 
            protocol specific.
        """
        handle = self.getHandle(discordUser)
        nick = self.getNick(discordUser)
        user = self.getUser(handle)

        logger.info("userSeenEntering: handle=%s, nick=%s, user=%s, channel=%s"%(handle,nick,user,channel))

        if channel:
            self.getLog(channel).online(user, nick)

        if user:
            user.profile.sign_on = datetime.now()
            user.profile.save()
            c = CommandContext(self, getChannelName(channel), user, nick, time.time())
            if user.id==self.user.id:
                await self.cmd.notifyListeners(c, "enter", message)
            else:
                await self.cmd.notifyListeners(c, "hearEnter", message)


    async def userSeenLeaving(self, discordUser, channel, *message):
        """ This Smaug event happens when a user disappears for
            some reason.
        """
        handle = self.getHandle(discordUser)
        nick = self.getNick(discordUser)
        user = self.getUser(handle)

        logger.info("userSeenLeaving: handle=%s, nick=%s, user=%s, channel=%s"%(handle,nick,user,channel))

        if channel:
            self.getLog(channel).offline(user, nick)

        if user:
            user.profile.sign_off = datetime.now()
            user.profile.save()
            c = CommandContext(self, getChannelName(channel), user, nick, time.time())
            if user.id==self.user.id:
                await self.cmd.notifyListeners(c, "exit", message)
            else:
                await self.cmd.notifyListeners(c, "hearExit", message)


    async def on_message(self, message):
        """ Recieved a message. It could be private or public.
        """
        # don't attempt to handle messages before we're ready for it
        if not self.ready: return 

        channel = message.channel 
        content = message.content 
        author = message.author
        handle = self.getHandle(author)
        nick = self.getNick(author)

        # log message for debugging
        logger.info("%s - %s (%s): %s" % (channel,nick,handle,content))

        user = self.getUser(handle)
        authed = False
        if user:
            authed = True
        else:
            user = self.cmd.getAnonUser(nick)

        context = CommandContext(self, getChannelName(channel), user, nick, time.time())
        cmd,args = findCommand(content)
        
        # log this event
        if channel.is_private: 
            log_msg = content
            if cmd and args: log_msg = "!%s [arguments hidden]" % cmd
            self.getLog(None).privateMessage(user,nick,log_msg,external_id=message.id)
        else: 
            serverName = channel.server.name
            self.getLog(channel).publicMessage(user,nick,content,external_id=message.id)

        # ignore commands from ourself
        if self.user and author.id==self.user.id:
            return

        # execute command or process event
        if authed and cmd:
            error = await self.cmd.execute(cmd, context, args, authed=authed)
            for msg in error:
                await context.reply(msg)
        else:
            await self.cmd.notifyListeners(context, "hear", content)

        if authed:
            user.profile.last_comment = datetime.now()
            user.profile.save()
  

    async def on_message_edit(self, before, after):
        """ Some message was edited
        """
        channel = before.channel 
        logger.info("Message %s was edited" % before.id)
        if before.content != after.content:
            logger.info("  Before: %s" % before.content)
            logger.info("  After: %s" % after.content)
            self.getLog(channel).editLine(after.content,external_id=before.id)
        elif not before.pinned and after.pinned:
            logger.info("  Now pinned")
        elif before.pinned and not after.pinned:
            logger.info("  Now unpinned")
        else:
            # TODO: implement other types of changes
            pass


    async def on_message_delete(self, message):
        """ Message was deleted 
        """
        channel = message.channel
        logger.info("Message %s was deleted" % message.id)
        self.getLog(channel).deleteLine(message.id)

    
    async def on_reaction_add(self, reaction, user):
        logger.info("Reaction %s added by user %s"%(reaction,user))


    async def on_reaction_remove(self, reaction, user):
        logger.info("Reaction %s removed by user %s" %(reaction, user))


    async def on_reaction_clear(self, message, reactions):
        logger.info("Reactions cleared: %s" % reactions)


    async def on_channel_update(self, before, after):
        logger.info("Channel was updated: %s", after)
        if before.topic != after.topic:
            self.getLog(after).topicChanged(after.topic.rstrip())
    

    async def die(self):
        logger.info("Quitting Discord")
        await self.logout()


    async def sendNotification(self, where, content, em=None):
        """ Implements protocol by redirecting to sendMessage.
        """
        await self.sendMessage(where, content, em=em)


    async def sendMessage(self, where, content, em=None):
        """ Implements protocol
        """
        line = self.getMessage(content)
        if line:
            target = where
            if isinstance(where, str):
                if where.startswith("#"):
                    # channel name was given
                    target = self.getDiscordChannelByName(where[1:])
                else:
                    # user name was given
                    target = self.getDiscordMemberByName(where)
                if not target:
                    raise Exception("Could not resolve target '%s'"%where)
            await self.send_message(target, line, embed=em)


    def getDiscordChannelByName(self, name):
        return discord.utils.get(self.get_all_channels(), name=name)


    def getDiscordMemberByName(self, name):
        for member in self.get_all_members():
            if member.name.lower() == name.lower():
                return member
            try:
                if member.nick.lower() == name.lower():
                    return member
            except:
                pass


    # Commands


    @command("version")
    @level(1)
    @usage("!version")
    @desc("Shows version and credits.")
    async def printVersion(self, c, args):
        version = settings.VERSION
        author = settings.AUTHOR
        f = self.format
        out  = u":dragon_face: :regional_indicator_s: :regional_indicator_m: :regional_indicator_a: "
        out += u":regional_indicator_u: :regional_indicator_g: :fire: last·of·the·great·fire·drakes "
        out += u":fire: °ver%s° [by %s]" % (version, f(author, bold=''))
        await c.reply(out)


    @command("say")
    @level(20)
    @usage("!say <text>")
    @desc("Have me say something in the channel.")
    async def doSay(self, c, args):
        if not args: raise CmdParamError
        if c.channel.startswith("#"):
            await self.sendMessage(c.channel, args)
        else:
            for channel in self.channels:
                await self.sendMessage(channel, args)


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
        await self.sendNotification(who, message)


    @command("playing")
    @level(20)
    @usage("!playing <game>")
    @desc("Mark me as playing a game.")
    async def doNotice(self, c, args):
        game = None
        if args:
            game = discord.Game(name=args)
        await self.change_presence(game=game)


    # Utilities


    def getChannel(self, channelName):
        if not channelName:
            return self.private_channel
        lc = channelName.lower()
        if lc in self.channels:
            return self.channels[lc]
        raise Exception("No such channel: "+channelName)


    def getLog(self, channel):
        channelName = getChannelName(channel)
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


    def getMessage(self, content):
        """ Converts content (string or array of strings) into a message
        """
        if isinstance(content, str):
            return content
        elif content:
            return "\n".join(content)
        else:
            raise Exception("Content is not string or iterable")


    def getNick(self, user):
        """ Given a discord.User, return the nick name they are going by.
        """
        nick = None
        try:
            nick = user.nick
            if not nick: nick = user.name
        except:
            nick = user.name
        return nick
    
    def getHandle(self, user):
        """ Given a discord.User, return the fully qualified
            name, with discriminator.
        """
        handle = user.name
        if user.discriminator:
            handle += "#%s" % user.discriminator  
        return handle


    def getUser(self, handle):
        """ Given a user discord handle, return the Smaug user object.
        """
        return self.cmd.getUserByHandle(handle)


    def formatSender(self, nick):
        """ Implements protocol
        """
        return "<%s> " % nick

    
    def format(self, s, **attrib):
        """ Implements protocol
        """
        if not s: return None
        codes = {
            'italic'     : '*',
            'bold'       : '**',
            'underline'  : '__',
        }

        for k in list(attrib.keys()):
            if k in codes:
                code = codes[k]
                s = code + s + code

        return s


