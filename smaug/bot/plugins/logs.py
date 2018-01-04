"""
Search through logs
"""

from smaug.bot import settings
from smaug.bot.command import *
from smaug.ircview import models

import random

class Logs(Plugin):

    def __init__(self):
        self.base_url = settings.WEB_BASE_URL
        self.bot_name = settings.BOT_NAME

    @command("logs")
    @level(2)
    @usage("!logs <search terms> [author]")
    @desc("Search the logs for some terms, with an optional author.")
    async def search(self, c, args):
 
        if not args:
            content = [
                "The latest logs are here: %s/latest/"%self.base_url,
                "You can use !logs <search terms> to search the logs." 
            ]
            await c.reply(content)
            return

        content = []
        searchText = args
        author = None

        args = args.strip()
        a = args.split(' ')

        if len(a)>1:
            handle = a[-1]
            users = models.SmaugUser.objects.filter(profile__handles__handle__exact=handle)
            if users:
                searchText = " ".join(a[0:-1])
                author = users[0]

        q = models.LogLine.objects.all()
        q = q.filter(body__search="%s"%searchText)
        if author:
            q = q.filter(user=author)
        q = q.exclude(user__name=self.bot_name)

        filtered = [line for line in q if not(line.body.startswith('!logs '))]
        count = len(filtered)

        url = "%s/search/?searchText=%s"%(self.base_url,searchText)
        if author:
            url += "&author=%s"% author.id

        content.append("%d hits; %s"%(count,c.protocol.format(url,color='fuchsia')))
        if count>0:
            r = random.randint(0, count-1)        
            rline = filtered[r]
            cl = "<%s> %s"%(rline.handle,rline.body)
            if rline.user:
                cl = c.protocol.format(cl,color=rline.user.profile.color)
            content.append("Random result: %s"%cl)

        await c.reply(content)



