"""
User messages
"""

from smaug.bot.command import *
from smaug.ircview import models

from datetime import datetime

class Messages(Plugin):

    def __init__(self):
        self.users = {}


    @listen("enter")
    async def hear(self, c, line):
        num = self.checkMessages(c, "")
        if num > 0 and c.user.id == c.cmd.me.id:
            c.reply("!read")
            await self.readMessages(c, str(num))


    @listen("hearEnter")
    async def hearEnter(self, c, message=""):
        if c.user.id not in self.users:
            self.users[c.user.id] = {}
        # only the last handle to sign on will get notifications, 
        # but this shouldn't be a problem since most people only
        # have one handle per protocol online at a time
        self.users[c.user.id][c.protocol.proto] = c
        await self.checkMessages(c, "")


    @listen("hearExit")
    async def hearExit(self, c, message=""):
        if c.protocol.proto in self.users[c.user.id]:
            del self.users[c.user.id][c.protocol.proto]


    @command("send")
    @level(2)
    @usage("!send <nick>,<nick>,... <message>")
    @desc("Sends a message to one or more people.")
    async def sendMessage(self, c, args):

        try:
            nicks, message = args.split(" ", 1)
        except ValueError:
            raise CmdParamError

        nicks = nicks.split(",")
        for nick in nicks:
            await self.sendMessageToNick(c, nick, message)


    async def sendMessageToNick(self, c, nick, message):

        to_user = c.protocol.cmd.getUserByHandle(nick)

        if not to_user:
            await c.reply("Unknown user.")
            return

        m = models.Message(from_user=c.user, to_user=to_user, body=message,
                           seen='N', passed='N', stamp=datetime.now())
        m.save()

        await c.reply("Message sent to %s."%nick)

        # now notify the recipient if they are online

        if to_user.id in self.users:
            for k in list(self.users[to_user.id].keys()):
                protocol = c.protocol.cmd.getProtocol(k)
                tc = self.users[to_user.id][k]
                if c.channel != tc.channel:
                    await tc.reply("New message for %s." \
                        % tc.user.name)


    @command("read")
    @level(2)
    @usage("!read [num]")
    @desc("Reads num messages (num default: 100)")
    async def readMessages(self, c, args):

        try:
            i = int(args.strip())
        except ValueError:
            i = 10

        j = 0
        
        messages = models.Message.objects.filter(to_user=c.user, seen='N').order_by('stamp')
        content = []

        if not messages: 
            content.append("No unread messages.")
        
        else:
            for m in messages:
                when = m.stamp.strftime("%m/%d/%y %H:%M")
                when = c.protocol.format(when, color='gray')

                m.seen = 'Y'
                m.passed = 'Y'
                m.save()

                content.append("%s [%s]: %s" % (m.from_user.username,when,m.body))
                j += 1
                if not i-j: break

            content.append("%s messages left." % (len(messages) - j))

        await c.reply(content)


    async def checkMessages(self, c, args):

        messages = models.Message.objects.filter(to_user=c.user, passed='N')
        if not messages: return

        for m in messages:
            m.passed = 'Y'
            m.save()

        messages = models.Message.objects.filter(to_user=c.user, seen='N')
        num = messages.count()

        if num == 0:
            # Message was already seen but not marked passed. This shouldn't happen, but if it does, we just cleaned it up, so no big deal.
            return

        if num == 1:
            await c.reply("Hi %s, you have a new message." % c.user.name)
        else:
            await c.reply("Hi %s, you have %s new messages." % (c.user.name,num))

        return num

