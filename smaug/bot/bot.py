#!/usr/bin/python

from smaug.bot import settings
from smaug.bot.irc import SmaugIRCFactory
from smaug.bot.discord import SmaugDiscord
from smaug.bot.command import *
from smaug.ircview import models

from django.contrib.auth.models import AnonymousUser
from functools import partial
from importlib import import_module,reload
from inspect import isclass

import os
import asyncio
import logging
import signal

logger = logging.getLogger(__name__)

class SmaugBot(object):
    
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.loop.set_debug(True)
        self.userCache = {}
        self.plugins = {}
        self.protocols = {}
        self.protocolModules = {}
        self.protocolCmds = {}
        self.listeners = {}
        self.cmds = {}
        self.dynamicCode = ""
        self.me = self.getUserByHandle(settings.BOT_NAME)

        logger.info("Starting Smaug Bot...")

        # set up the event types 
        for eventType in EVENT_TYPES:
            self.listeners[eventType] = {}

        # add ourselves as a plugin
        logger.info("Loading module smaug")
        self.addPlugin("smaug", self)

        if 'irc' in settings.PROTOCOLS:
            # instantiate IRC client factory
            self.irc = SmaugIRCFactory(self,
                    settings.IRC_NICK,
                    settings.IRC_PASSWORD,
                    settings.IRC_SERVER,
                    settings.IRC_PORT,
                    settings.IRC_CHANNELS,
                    settings.IRC_QUIT_MESSAGES,
                    settings.IRC_LOGDIR)
            self.initProtocol("irc", settings.IRC_MODULES)

        if 'discord' in settings.PROTOCOLS:
            # instantiate Discord client directly
            self.discord = SmaugDiscord(self, 
                    settings.DISCORD_TOKEN,
                    settings.DISCORD_CHANNELS,
                    settings.DISCORD_ALERTS,
                    settings.DISCORD_LOGDIR)
            self.initProtocol("discord", settings.DISCORD_MODULES)


    def initProtocol(self, proto, moduleNames):
        self.protocolCmds[proto] = {}
        self.addModule(proto, "smaug")
        for moduleName in moduleNames:
            self.addModule(proto, moduleName)

    
    def addModule(self, proto, moduleName):
        """ Mark the functions from a given module as accessible 
            to a protocol.
        """

        if proto not in settings.PROTOCOLS:
            raise Exception("Invalid protocol: %s"%proto)

        # Load the plugin if it hasn't been loaded
        self.getPlugin(moduleName)

        # Track all modules added to a protocol
        if proto not in self.protocolModules:
            self.protocolModules[proto] = []
        self.protocolModules[proto].append(moduleName)

        for f in self.cmds[moduleName]:
            if f.command in self.protocolCmds[proto]:
                logger.info("    Redefining command %s for protocol %s" % (f.command,proto))
            else:
                logger.info("    Adding command %s for protocol %s" % (f.command,proto))
            self.protocolCmds[proto][f.command] = f


    def getPlugin(self, moduleName):
        """ Returns the shared instance of a given plugin. 
            If no instance currently exists, then it is first created.
        """
        if moduleName not in self.plugins:
            logger.info("Loading plugin %s", moduleName)
            module = import_module("smaug.bot.plugins."+moduleName)
            plugin = self.newPlugin(module)
            self.addPlugin(moduleName, plugin)
        return self.plugins[moduleName]


    def newPlugin(self, module):
        for name in dir(module):
            c = getattr(module,name)
            if isclass(c) and (Plugin in c.__bases__):
                return c()
        raise Exception("Module %s does not define a Plugin" % module)


    def addPlugin(self, moduleName, plugin):
        self.plugins[moduleName] = plugin
        self.addListeners(moduleName, plugin)
        self.cmds[moduleName] = []
        for f in self.getPluginFunctions(plugin,'command'):
            logger.debug("    Adding command %s",f.command)
            self.cmds[moduleName].append(f)


    def addListeners(self, moduleName, plugin):
        for function in self.getPluginFunctions(plugin,'listen'):
            if not(function.eventType in EVENT_TYPES):
                raise Exception("Unrecognized event type: %s" % function.eventType)
            else:
                if moduleName in self.listeners[function.eventType]:
                    logger.info("    Redefining %s listener for module %s",function.eventType,moduleName)
                else:
                    logger.info("    Adding %s listener for module %s",function.eventType,moduleName)
                self.listeners[function.eventType][moduleName] = function


    def getPluginFunctions(self, plugin, tag):
        return [getattr(plugin,m) for m in dir(plugin) if hasattr(getattr(plugin,m),tag)]


    def registerProtocol(self, protocol):
        """ A protocol calls this once it makes a connection
            to make itself known to us.
        """
        proto = protocol.proto
        logger.info("Registering protocol: %s",proto)
        self.protocols[proto] = protocol
        self.addPlugin(proto, protocol)
        self.addModule(proto, proto)


    def getProtocol(self, proto):
        """ Return a protocol given a name
            The protocol must have already connected and 
            registered with registerProtocol()
        """
        if proto in self.protocols:
            return self.protocols[proto]
        else:
            return None
        

    def getUserByHandle(self, handle):
        h = handle.split("|", 1)
        users = models.SmaugUser.objects.filter(profile__handles__handle__exact=h[0].lower())
        if users: return users[0]
        return None


    def getUser(self, userId):
        """ Return a user with the given userId
        """
        if not userId: return None
        user = None
        if userId in self.userCache:
            user = self.userCache.get(userId)
        else:
            users = models.SmaugUser.objects.filter(id__exact=userId)
            if users:
                user = users[0]
                self.userCache[userId] = user
        return user
    

    def getAnonUser(self, username):
        """ Returns an anonymous user
        """
        user = AnonymousUser()
        user.username = username
        return


    def authHost(self, user, userhost):
        """ Given a user and host, attempt to authenticate against
            the hosts database.
        """
        if not user: return False
        hosts = list(user.profile.hosts.all())
        if hosts:
            for h in hosts:
                p = h.host.replace(".","\.").replace("*","(.*?)")
                if re.compile(p).match(userhost):
                    return True
        else:
            logger.info("Adding host %s for first time user %s"%(userhost,user.username))
            host = models.IrcUserHost(profile=user.profile, host=userhost)
            host.save()
            return True

        return False


    async def notifyListeners(self, context, eventType, message=""):
        """ Whenever a protocol receives input it
            should call this method to notify any listeners.
            event can be hear, hearEnter, or hearExit 
        """
        for moduleName in self.listeners[eventType]:
            try:
                callback = self.listeners[eventType][moduleName]
                await callback(context, message)
            except Exception as e:
                await context.reply("%s: %s" % (e.__class__, e))
                logger.exception("Error notifying listeners")


    async def execute(self, cmd, c, args, authed=True):
        """ execute a command on behalf of an interface
            command: name of command to execute
            c: Commandc describing the enviroment
            args: command arguments as a string
            authed: boolean indicating if the user was actually authenticated. 
                This flag is only checked if the command's access level is 
                ACCESS_NEEDS_AUTH or greater and the user has access to it.
        """
        try:
            try:
                f = self.protocolCmds[c.protocol.proto][cmd]
            except KeyError:
                return ["Not a valid command"]
            
            if not c.user or c.user.profile.access < f.level:
                return ["Insufficient privileges"]
                
            if f.level >= settings.ACCESS_NEEDS_AUTH:
                if not authed:
                    return ["You must authenticate to run this method."]

            try:
                if not args: args = ""
                logger.info("calling %s.%s for %s",f.__module__, f.__name__, c.user.username)
                await f(c, args)
                return []
            except CmdParamError:
                return ["Usage: %s" % f.usage]
            except CmdExeError as e:
                return ["%s" % e]

        except Exception as e:
            logger.exception("Error executing command")
            return ["%s: %s" % (e.__class__, e)]


    async def closeClients(self):
        """ Close all clients """
        logger.debug("Will close clients: %s"%self.protocols.keys())
        for proto in list(self.protocols.values()):
            logger.debug("Awaiting %s client's demise" % proto.proto)
            await proto.die()
        self.discord.close()
        logger.debug("All clients are now closed")


    async def shutdown(self):
        logger.info("Shutting down...")
        try:
            # Wait until each client dies
            await self.closeClients()
            # Gather all remaining tasks and cancel them
            pending = [t for t in asyncio.Task.all_tasks(loop=self.loop) if t is not asyncio.tasks.Task.current_task()]
            gathered = asyncio.gather(*pending, loop=self.loop)
            gathered.cancel()
            logger.debug("Waiting for remaining tasks...")
            try:
                await gathered
                # we want to retrieve any exceptions to make sure that
                # they don't nag us about it being un-retrieved.
                gathered.exception()
            except asyncio.CancelledError:
                # This is expected
                pass
        except Exception as e:
            logger.exception("Exception while shutting down")
        finally:
            logger.info("Clean up operations complete. Exiting.")
            self.loop.stop()


    def run(self):
        """ lets get this party started """
        try:
            self.loop.add_signal_handler(signal.SIGINT,
                    partial(asyncio.ensure_future, self.shutdown()))
            if 'irc' in settings.PROTOCOLS:
                self.irc.startBot()
            if 'discord' in settings.PROTOCOLS:
                asyncio.ensure_future(self.discord.startBot(), loop=self.loop)
            # run the main event loop
            self.loop.run_forever()

        except KeyboardInterrupt:
            logger.info("Caught keyboard interrupt")
            self.loop.run_until_complete(self.shutdown())


    ## BUILTIN PLUGIN FUNCTIONS ##

    @command("die")
    @level(50)
    @usage("!die")
    @desc("Die!")
    async def die(self, c=None, args=None):
        # Using the following line results in the annoying warning 
        # "shutdown was never awaited"
        #await self.shutdown()
        # Instead, we can trigger shutdown by using a SIGINT:
        os.kill(os.getpid(), signal.SIGINT)


    @command("help")
    @level(1)
    @usage("!help")
    @desc("""Without arguments this will give you an index of commands. 
             Specify a command to learn more about it.""")
    async def help(self, c, args):
        cmd = args.strip()
        proto = c.protocol.proto

        if cmd:
            try:
                func = self.protocolCmds[proto][cmd]
            except KeyError:
                await c.notify("Not a valid command")
                return

            if func.level > c.user.profile.access: return
            await c.notify("Usage: %s\n%s" % (func.usage,func.desc))
        else:
            f = c.protocol.format
            content = ["Available commands:"]
            for moduleName in self.plugins:
                if moduleName in self.protocolModules[proto]:
                    names = []
                    for func in self.cmds[moduleName]:
                        if func.command in self.protocolCmds[proto]:
                            names.append(func.command)
                    
                    if len(names):
                        names.sort()
                        commands = ["!%s"%n for n in names]
                        content.append("%s: %s" %(f(moduleName,bold=''),", ".join(commands)))
            
            await c.notify(content)
    

    @command("modules")
    @level(20)
    @usage("!modules")
    @desc("List the loaded module plugins")
    async def listModules(self, c, args):
        await c.reply("Loaded modules:\n%s" % "\n".join(list(self.plugins.keys())))
 

    @command("load")
    @level(50)
    @usage("!load <module> <protocol>")
    @desc("Load a module and make it available in a certain protocol")
    async def loadModule(self, c, args):
        try:
            moduleName,protoName = args.split(' ')
        except ValueError:
            raise CmdParamError

        proto = protoName.strip()
        self.addModule(proto, moduleName)
        await c.reply("Added module %s to %s" % (moduleName,proto))


    @command("reload")
    @level(50)
    @usage("!reload <module>")
    @desc("Reload a module")
    async def reloadModule(self, c, args):
        moduleName = args.strip()
        if not moduleName:
            raise CmdParamError
        if moduleName == "smaug": 
            raise CmdExeError("Built-in module cannot be reloaded")

        module = import_module("smaug.bot.plugins."+moduleName)
        try:
            reload(module)
            self.addPlugin(moduleName, self.newPlugin(module))

            # load the module for every protocol that needs it, 
            # to refresh the functions
            for proto in settings.PROTOCOLS:
                if moduleName in self.protocolModules[proto]:
                    self.addModule(proto, moduleName)

            await c.reply(moduleName + " has been reloaded.")
        except (SyntaxError, ImportError) as e:
            await c.reply(str(e))


    @command("tasks")
    @level(50)
    @usage("!tasks")
    @desc("Show pending async tasks")
    async def showTasks(self, c, args):
        for t in asyncio.Task.all_tasks(loop=self.loop):
            await c.reply("  %s"%t)

