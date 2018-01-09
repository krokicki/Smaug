"""
Utilities for dealing with URLS.
"""

from smaug.bot.command import *

import urllib.request
from smaug.utils.urls import findUrls

MAX_URLS = 5

class Urls(Plugin):

    def __init__(self):
        self.opener = urllib.request.build_opener()
        self.urls = []
     

    @listen("hear")
    async def hear(self, c, line):
        urls = findUrls(line)
        self.urls.extend(urls)
        if c.protocol.proto=='irc':
            content = []
            for url in urls:
                if len(url) > 90:
                    content.append(self.createTinyUrl(url))
            await c.reply(content)


    @command("tiny")
    @level(1)
    @usage("!tiny <url>")
    @desc("Creates a tiny URL from a large one. If no URL is provided then the last URL spoken in the channel is used.")
    async def tinyUrl(self, c, args):

        content = []
        urls = findUrls(args)
        if urls:
            for url in urls:
                content.append(self.createTinyUrl(url))
        else:
            content.append(self.createTinyUrl(self.urls[-1]))

        await c.reply(content)


    @command("urls")
    @level(1)
    @usage("!urls [num]")
    @desc("Lists the last [num] URLs spoken in the channel. If no number if given, 10 URLs are displayed.")
    async def showUrls(self, c, args):

        content = []
        try:
            num = int(args.strip())
        except:    
            num = 3

        if num > len(self.urls):
            num = len(self.urls)

        if num > MAX_URLS:
            num = MAX_URLS

        start = len(self.urls) - num

        for i in range(start,len(self.urls)):
            content.append(self.urls[i])

        await c.reply(content)


    def createTinyUrl(self, url):
        req = urllib.request.Request('http://tinyurl.com/api-create.php?url='+url)
        return "%s"%self.opener.open(req).read().decode("utf-8")


