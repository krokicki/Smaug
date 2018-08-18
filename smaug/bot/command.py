""" Plugins, commands, and events.
"""

import re
import collections

EVENT_TYPES = ('joined','enter','exit','hear','hearEnter','hearExit',)

class Plugin(object):
    """ Extending this class simply marks it as a Smaug plugin. 
        It must also define a no-arg constructor so that it can be 
        instantiated by the framework. Methods on the plugin may be 
        marked with @command or @listen decorations in order to 
        expose them to the bot framework. 
    """
    pass


class CmdParamError(Exception):
    """ Incorrect number/type of command arguments 
        This should result in a "usage" message.
    """
    pass


class CmdExeError(Exception):
    """ Command did not execute correctly """
    pass



def findCommand(line):
    """ Utility function which reads 
        a line of user input and returns the embedded
        command, if any.
    """

    p = re.compile(r"^!(\w+)(\s(.*))?$")
    m = p.search(line)

    if m and m.group(1):
        return m.group(1),m.group(3)
    else: 
        return "",""



class CommandContext(object):
    """ All the variables related to the context of the command.
        The protocol, channel (none if private), the user and
        the user's alias when issuing the command.

        Note that, this object is also used for notifications which 
        aren't really commands (like joins), so "command" is sort of 
        a misnomer. Luckily, I don't care.
    """

    def __init__(self, protocol, channel, user, alias, when):
        self.protocol = protocol 
        self.channel = channel
        self.user = user
        self.alias = alias
        self.when = when


    async def reply(self, content, em=None):
        """ Reply to the user or channel the user executed
            the command in.
        """
        if content:
            content = convertFromUnicode(content)
            where = self.channel or self.alias
            f = self.protocol.sendMessage(where, content, em=em)
            if f: await f


    async def notify(self, content, em=None):
        """ Reply directly to the user regardless of channel context
            and alert him if possible.
        """
        if content:
            content = convertFromUnicode(content)
            where = self.alias
            f = self.protocol.sendNotification(where, content, em=em)
            if f: await f


def command(name):
    """ Decoration which marks a method as a bot command available as "!name <args>"
        The method must take take parameters (self, c, args) where c is the 
        CommandContext and args are the raw arguments provided by the user.
    """
    def _decoration(fcn):
        fcn.command = name
        return fcn
    return _decoration


def level(levelValue):
    """ Decorates a command with the authorization level required to run the command.
    """
    def _decoration(fcn):
        fcn.level = levelValue
        return fcn
    return _decoration


def usage(text):
    """ Decorates a command with a usage message that is printed when the user 
        calls !help
    """
    def _decoration(fcn):
        fcn.usage = text
        return fcn
    return _decoration


def desc(text):
    """ Decorates a command with a description message that is printed when the user
        calls !help
    """
    def _decoration(fcn):
        fcn.desc = text
        return fcn
    return _decoration


def listen(eventType):
    """ Decorates a method as listening to events of a particular type. 
    """
    def _decoration(fcn):
        fcn.listen = True
        fcn.eventType = eventType
        return fcn
    return _decoration


def convertFromUnicode(content):
    """ Who the hell knows what might be coming in. 
        One of these has gotta work.
    """
    return content


