"""
Inter-Protocol Tunnels (IPTs) are used for user communication across
protocols. A user opens tunnels to whoever they want and then everything
they type is transmitted to all the listening parties. Both sides
have the ability to close a tunnel.
"""

from smaug.bot.command import *

import logging

logger = logging.getLogger(__name__)

class Tunnels(Plugin):

    def __init__(self):
        self.tunnels = {}
 
       
    @listen("hear")
    async def hear(self, c, line):
        """ Check if the sender has any open tunnels 
            thru which to transmit this message.
        """
        # check the sender's open tunnels
        tunnels = self.getTunnels(c.user, c.protocol) 
        if tunnels:
            for tunnel in tunnels:
                await tunnel.printLine(line)

                # check for a chunnel :o
                # I mean, this tunnel might go into a channel which 
                # has outgoing tunnels that need to be written
                to = tunnel.toParty
                if to.channel:
                    chunnels = self.getTunnels(None, to.protocol)
                    for chunnel in chunnels:
                        if (chunnel.fromParty.channel == to.channel) and \
                                not(chunnel.toParty == tunnel.fromParty):
                            fc = CommandContext(c.protocol, chunnel.fromParty.channel,
                                c.user, c.alias, None)
                            await chunnel.printChannelLine(fc,line)

        # also check for channel tunnels
        tunnels = self.getTunnels(None, c.protocol)
        if tunnels:
            for tunnel in tunnels:
                if c.channel == tunnel.fromParty.channel:
                    await tunnel.printChannelLine(c,line)


    @listen("hearExit")
    async def hearExit(self, c, message=""):
        """ Listen for users signing off, 
            so that tunnels can be cleaned up.
        """
        tunnels = self.getTunnels(c.user, c.protocol)
        if tunnels:
            # close the sender's open tunnels
            toDelete = tunnels[:]
            for tunnel in toDelete:
                await tunnel.messageReceiver("%s has signed off. Tunnel closed." % \
                    (tunnel.fromParty.getName()))
                self.collapseTunnel(tunnel)
        

    @command("tunnels")
    @level(0)
    @usage("!tunnels")
    @desc("Lists all your open tunnels.")
    async def listTunnels(self, c, args):

        fromParty = self.getFromParty(c)
        tunnels = self.getTunnels(fromParty.user, fromParty.protocol)

        content = []
        if not tunnels:
            content.append("No active tunnels")
        else:
            content.append("Active tunnels:")
            for tunnel in tunnels:
                content.append("  %s" % tunnel.toParty)

        await c.reply(content)


    @command("_tunnels")
    @level(10)
    @usage("!_tunnels")
    @desc("Lists all open tunnels.") 
    async def listAllTunnels(self, c, args):

        tunnels = []
        for user in self.tunnels:
            for proto in self.tunnels[user]:
                tunnels += self.tunnels[user][proto]

        content = []
        if not tunnels:
            content.append("No active tunnels")
        else:
            content.append("%d active tunnels:"%len(tunnels))
            for tunnel in tunnels:
                content.append("  %s" % tunnel)

        await c.reply(content)


    @command("tunnel")
    @level(2)
    @usage("!tunnel <proto:target>")
    @desc("Opens an inter-protocol tunnel. Target may be a nickname or channel.") 
    async def openTunnel(self, c, args):

        try:
            tproto, target = args.strip().split(":",1)
        except ValueError:
            raise CmdParamError

        if not(tproto and target and tproto in c.protocol.cmd.protocols): 
            c.reply("Cannot resolve user/protocol")
            return
            
        targetProtocol = c.protocol.cmd.getProtocol(tproto)
        
        if target.startswith("#"):
            if target in targetProtocol.channels:
                await self.openIPT(c, targetProtocol, target)
            else:
                await c.reply("Channel %s does not exist on protocol %s"%(target,tproto))
        else:
            # We should query the protocol here to make sure we have access to the target
            await self.openIPT(c, targetProtocol, target)
        

    def getFromParty(self, c):
        """ Create a Party object representing the current request
        """

        if str(c.channel).startswith("#"):
            source = None
            sourceUser = None
        else:
            source = c.alias
            sourceUser = c.user

        return Party(source, sourceUser, c.protocol, c.channel)


    def getToParty(self, c, protocol, target):
        """ Create a Party object representing the given protocol:target,
            where target is either a channel name starting with #, or a user handle.
        """

        cmd = c.protocol.cmd

        if target.startswith("#"):
            targetChannel = target
            targetUser = None
            target = None
        else:
            targetChannel = None
            targetUser = cmd.getUserByHandle(target)
            if not targetUser:
                user = cmd.getAnonUser(target)

        return Party(target, targetUser, protocol, targetChannel)


    async def openIPT(self, c, targetProtocol, target):
        """ Open a tunnel from the current request to the target
        """

        fromParty = self.getFromParty(c)
        toParty = self.getToParty(c, targetProtocol, target)

        # establish tunnel
        ipt = IPT(fromParty, toParty)
        tunnels = self.getTunnels(fromParty.user, fromParty.protocol)
        tunnels.append(ipt)
        logger.info("Established tunnel: %s" % ipt)
        
        # reverse tunnel
        ript = IPT(toParty, fromParty)
        rtunnels = self.getTunnels(toParty.user, toParty.protocol)
        rtunnels.append(ript)
        logger.info("Established tunnel: %s" % ript)

        # mmm, circular references
        ipt.setReverse(ript)
        ript.setReverse(ipt)

        openMessage = "Tunnel open to %s. Type !close to end this session."
        await ipt.messageSender(openMessage % toParty)
        await ipt.messageReceiver(openMessage % fromParty)

 
    @command("close")
    @level(0)
    @usage("!close [proto:target]")
    @desc("Closes an inter-protocol tunnel. Proto and target are optional. If omitted, all tunnels are closed.") 
    async def closeIPT(self, c, args):

        try:
            tproto, target = args.strip().split(":",1)
            closeAll = 0
        except ValueError:
            tproto = None
            target = None
            closeAll = 1

        fromParty = self.getFromParty(c)
        tunnels = self.getTunnels(fromParty.user, fromParty.protocol)

        toDelete = []
        for tunnel in tunnels:
            to = tunnel.toParty
            
            if closeAll or \
                (tproto == to.protocol.proto and target == to.alias):
                
                # this tunnel is safe to delete
                toDelete.append(tunnel)

        closeMessage = "Closed tunnel to %s"
        for tunnel in toDelete:
            self.collapseTunnel(tunnel)
            await tunnel.messageSender(closeMessage % tunnel.toParty)
            await tunnel.messageReceiver(closeMessage % tunnel.fromParty)


    def collapseTunnel(self, tunnel):
        """ Close both ends of the given tunnel
        """
        rtunnel = tunnel.getReverse()

        user = tunnel.fromParty.user
        ruser = rtunnel.fromParty.user
        proto = tunnel.fromParty.protocol.proto
        rproto = rtunnel.fromParty.protocol.proto

        logger.info("Closing tunnel: %s" % tunnel)
        self.tunnels[user][proto].remove(tunnel)

        logger.info("Closing tunnel: %s" % rtunnel)
        self.tunnels[ruser][rproto].remove(rtunnel)


    def getTunnels(self, user, protocol):
        """ Get a list of tunnels for a user on a protocol
        """

        if user:
            uid = user.id
        else:
            uid = "None"

        if user not in self.tunnels:
            self.tunnels[user] = {}

        proto = protocol.proto
        if proto not in self.tunnels[user]:
            self.tunnels[user][proto] = []

        tunnels = self.tunnels[user][proto]
        logger.debug("Got tunnels for user %s on %s: %s"%(user,proto,tunnels))
        return tunnels



class IPT:
    """ And Inter-Protocol Tunnel
    """
    
    def __init__(self, fromParty, toParty):
        """ Create an IPT
        """
        self.fromParty = fromParty
        self.toParty = toParty
        self.rtunnel = None


    def setReverse(self, rtunnel):
        """ Set the reverse tunnel
        """
        self.rtunnel = rtunnel


    def getReverse(self):
        """ Get the reverse tunnel
        """
        return self.rtunnel
       

    async def printLine(self, line):
        """ Send a message thru the tunnel.
        """
        sender = self.fromParty.protocol.formatSender(self.fromParty.alias)
        text = sender + self.toParty.protocol.format(line)
        
        userColor = self.fromParty.user.profile.color
        if userColor:
            text = self.toParty.protocol.format(text, color=userColor)
            
        await self.messageReceiver(text)
 
 
    async def printChannelLine(self, c, line):
        """ 
        This is a special method for tunnels in which the fromParty 
        is a channel. It uses the given context to determine the 
        actual sender and qualifies the alias with the channel.
        """
        if c.channel != self.fromParty.channel:
            raise ValueError("context does not match IPT")

        sender = c.protocol.formatSender("%s:%s"%(c.channel,c.alias))
        text = sender + self.toParty.protocol.format(line)
        
        userColor = c.user.profile.color
        if userColor:
            text = self.toParty.protocol.format(text, color=userColor)
        else:
            text = self.toParty.protocol.format(text)
         
        await self.messageReceiver(text)
        
        
    async def messageSender(self, line):
        channel = self.fromParty.channel or self.fromParty.alias
        protocol = self.fromParty.protocol
        await protocol.sendMessage(channel, self.fromParty.protocol.format(line))
        
        
    async def messageReceiver(self, line):
        channel = self.toParty.channel or self.toParty.alias
        protocol = self.toParty.protocol
        await protocol.sendMessage(channel, line)
 

    def __repr__(self):
        return "%s -> %s" % (self.fromParty, self.toParty)


class Party:
    """ A user on a certain protocol
        The channel can be empty for private messages, otherwise 
        it should just be the name of the channel the user is typing in.

        Also, the alias/user can be None and the party would be 
        the entire channel.

        Examples:
            alias = "kradAim"     alias = "krad|work"
            user = krad           user = krad
            protocol = aim        protocol = irc
            channel = ""          channel = "#smaug"
    """

    def __init__(self, alias, user, protocol, channel):
        self.alias = alias
        self.user = user
        self.protocol = protocol
        self.channel = channel


    def getName(self):
        return self.alias or self.channel


    def __repr__(self):
        return "%s:%s" % (self.protocol.proto, self.getName())

