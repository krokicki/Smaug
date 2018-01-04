"""
User management (handles, hosts, event times)
"""

from smaug.bot.command import *
from smaug.ircview import models

import logging

logger = logging.getLogger(__name__)

class UserTools(Plugin):

    @command("_adduser")
    @level(15)
    @usage("!_adduser <nick> <name>")
    @desc("Adds the given user, using their current handle as the username.")
    async def addUser(self, c, args):

        try:
            nick, name = args.strip().split(" ", 1)
        except ValueError:
            raise CmdParamError

        handle = nick.split("|", 1)[0]
        user = models.SmaugUser.objects.create_user(handle, name=name)
        user.save()
        profile = user.profile
        handle = models.SmaugUserHandle(profile=profile, handle=handle, proto=c.protocol.proto)
        handle.save()
        await c.reply("Added user %s" % user.username)


    @command("addhost")
    @level(10)
    @usage("!addhost <user@host>")
    @desc("Associates a host with your username. The user@host may contain wildcards.")
    async def addHost(self, c, args):
        await self.addUserHost(c, c.user.username + " " + args)
 

    @command("delhost")
    @level(10)
    @usage("!delhost <user@host>")
    @desc("Deletes a host from your allowed host list.")
    async def deleteHost(self, c, args):
        await self.deleteUserHost(c, c.user.username + " " + args)
       
   
    @command("listhosts")
    @level(9)
    @usage("!listhosts")
    @desc("Lists the hosts associated with your username.")
    async def listHosts(self, c, args):
        await self.listUserHosts(c, str(c.user.username))
       

    @command("_addhost")
    @level(15)
    @usage("!_addhost <user> <user@host>")
    @desc("Add a host for the user.")
    async def addUserHost(self, c, args):

        try:
            handle, host = args.split(" ", 1)
            handle = handle.strip()
            host = host.strip()
        except ValueError:
            raise CmdParamError
         
        if not handle: raise CmdParamError("Must specify a user")
        if not host: raise CmdParamError("Must specify a host")
        if " " in handle: raise CmdParamError("Handle may not contain spaces.")

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user: %s"%handle)

        profile = user.profile

        if profile.access > c.user.profile.access:
            await c.reply("You may not add hosts for users with more access than you.")
            return
         
        try:
            host = models.IrcUserHost(profile=profile, host=host)
            host.save()
            await c.reply("Added host %s for %s" % (host.host,handle))
        except Exception as e:
            await c.reply("Error adding host: %s"%e)


    @command("_delhost")
    @level(15)
    @usage("!_delhost <user> <user@host>")
    @desc("Delete a host for the user.")
    async def deleteUserHost(self, c, args):

        try:
            handle, host = args.split(" ", 1)
        except ValueError:
            raise CmdParamError

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user: %s"%handle)

        profile = user.profile

        content = []
        hosts = list(profile.hosts.filter(host=host))
        if not hosts:
            content.append("No such host: %s"%host)
        else:
            for h in hosts:
                try:
                    h.delete()
                    content.append("Deleted host %s"% h.host)
                except Exception as e:
                    content.append("Error deleting host: %s"%e)

        await c.reply(content)


    @command("_listhosts")
    @level(15)
    @usage("!_listhosts <user>")
    @desc("Lists the allowed hosts for the user.")
    async def listUserHosts(self, c, args):

        handle = args.strip()
        if not handle: raise CmdParamError

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user: %s"%handle)
 
        profile = user.profile
        hosts = profile.hosts.all()

        content = []
        if len(hosts) == 0:
            content.append("No hosts defined")
        else:
            content.append("Hosts for %s: " % handle)
            for host in hosts:
                content.append("  %s\n" % host.host)
               
        await c.reply(content)

    @command("_access")
    @level(15)
    @usage("!_access <user> [new_level]")
    @desc("Get or set the access level for a user.")
    async def editUserAccess(self, c, args):

        try:
            handle, levelStr = args.strip().split(" ", 1)
        except ValueError:
            if args.strip():
                handle = args.strip()
                levelStr = None
            else:
                raise CmdParamError

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user: %s"%handle)
         
        profile = user.profile
        content = []

        if not levelStr:
            content.append("Current access level is %s" % profile.access)
        else:
            if int(levelStr) > int(c.user.profile.access):
                c.reply("You may not instill greater power than you possess.")
                return
             
            try:   
                profile.access = int(levelStr)
                profile.save()
                content.append("Updated %s's access to %s" % (handle,levelStr))
            except Exception as e:
                content.append("Error updating user: %s"%e)

        await c.reply(content)


    @command("addhandle")
    @level(10)
    @usage("!addhandle <handle> <protocol>")
    @desc("Add a handle (alias) for yourself.")
    async def addHandle(self, c, args):
        return await self.addUserHandle(c, c.alias + " " + args)
       

    @command("delhandle")
    @level(10)
    @usage("!delhandle <handle> <protocol>")
    @desc("Deletes a handle (alias).")
    async def deleteHandle(self, c, args):
        return await self.deleteUserHandle(c, c.alias + " " + args)
       
       
    @command("listhandles")
    @level(9)
    @usage("!listhandles")
    @desc("""Lists your handles (aliases). A handle is any nickname you wish to identify you. 
             When processing a nickname, everything after a pipe (\"|\") is ignored.""")
    async def listHandles(self, c, args):
        return await self.listUserHandles(c, str(c.alias))
       

    @command("_addhandle")
    @level(15)
    @usage("!_addhandle <user> <handle> <protocol>")
    @desc("Add a handle for the user.")
    async def addUserHandle(self, c, args):

        try:
            userHandle, handle, proto = args.split(" ", 2)
        except ValueError:
            raise CmdParamError
        
        if not userHandle: raise CmdParamError("Must specify a user")
        if not handle: raise CmdParamError("Must specify a handle")
        if not proto: raise CmdParamError("Must specify a protocol")
        if " " in handle: raise CmdParamError("Handle may not contain spaces.")

        if not(proto in c.protocol.cmd.protocols):
            raise CmdExeError("No such protocol: %s"%proto)
         
        user = c.protocol.cmd.getUserByHandle(userHandle)
        if not user: 
            raise CmdExeError("No such user handle: %s"%userHandle)
     
        profile = user.profile
        content = []

        try: 
            handle = models.SmaugUserHandle(profile=profile, handle=handle, proto=proto)
            handle.save()
            content.append("Added handle %s for %s on %s." % (handle.handle,userHandle,proto))
        except Exception as e:
            content.append("Error adding user handle: %s"%e)
        
        await c.reply(content)


    @command("_delhandle")
    @level(15)
    @usage("!_delhandle <user> <handle> <protocol>")
    @desc("Delete a handle for the user.")
    async def deleteUserHandle(self, c, args):

        try:
            userHandle, handle, proto = args.split(" ", 2)
        except ValueError:
            raise CmdParamError
       
        cmd = c.protocol.cmd
        
        if not(proto in cmd.protocols):
            raise CmdExeError("No such protocol: %s"%proto)
            
        user = c.protocol.cmd.getUserByHandle(userHandle)
        if not user: 
            raise CmdExeError("No such user handle: %s"%userHandle)
     
        profile = user.profile
        content = []

        try: 
            handles = profile.handles.filter(handle=handle, proto=proto)
            if handles:
                for h in handles:
                    h.delete()                
                    content.append("Deleted handle %s for %s on %s." % (handle,userHandle,proto))
            else:
                content.append("No such handle for user: %s"%handle)
        except Exception as e:
            content.append("Error deleting user handle: %s"%e)
 
        await c.reply(content)


    @command("_listhandles")
    @level(15)
    @usage("!_listhandles <user>")
    @desc("Lists the handles for the user.")
    async def listUserHandles(self, c, args):

        handle = args.strip()
        if not handle: raise CmdParamError

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user handle: %s"%handle)
     
        profile = user.profile
        content = []

        handles = list(profile.handles.all())
        if not handles:
            content.append("No handles defined")
        else:
            content.append("Handles for %s: " % user.name)
            hmap = {}
            for handle in handles:
                proto = handle.proto
                if proto not in hmap: hmap[proto] = []
                hmap[proto].append(handle.handle)
    
            for proto in sorted(hmap.keys()):
                content.append("  " + proto + ": " + ", ".join(hmap[proto]))
            
        await c.reply(content)

    @command("heard")
    @level(1)
    @usage("!heard <handle>")
    @desc("When did I last hear from this person?")
    async def lastHeardUser(self, c, args):
        arg = str(args.strip())
        handle = arg.split("|", 1)[0]
        if not handle: raise CmdParamError

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user: %s"%handle)
 
        profile = user.profile
        content = []

        if profile.last_comment:
            when = profile.last_comment.strftime("on %m/%d/%Y at %I:%M %p")
            content.append("I last heard from %s %s."%(user.name,when))  
        else:
            content.append("I have no idea when %s last spoke."%user.name)
    
        await c.reply(content)
            
    @command("seen")
    @level(1)
    @usage("!seen <handle>")
    @desc("When did I see this person last?")
    async def lastSeenUser(self, c, args):
        arg = str(args.strip())
        handle = arg.split("|", 1)[0]
        if not handle: raise CmdParamError

        user = c.protocol.cmd.getUserByHandle(handle)
        if not user: 
            raise CmdExeError("No such user: %s"%handle)
 
        profile = user.profile
        content = []

        if profile.sign_off:
            if profile.sign_on>profile.sign_off:
                when = profile.sign_on.strftime("on %m/%d/%Y at %I:%M %p")
                content.append("%s is here. They signed in %s."%(user.name,when))
            else:
                when = profile.sign_off.strftime("on %m/%d/%Y at %I:%M %p")
                content.append("I last saw %s %s."%(user.name,when))  
        else:
            content.append("I haven't seen %s."%user.name)

        await c.reply(content)


