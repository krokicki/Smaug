"""
Linking to quotes
"""

from smaug.bot.command import *
from smaug.ircview import models

from aiohttp import ClientSession
from discord import Embed
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

class QuoteLink(Plugin):

    def __init__(self):
        pass

    @listen("hear")
    async def hear(self, c, line):

        # quote must be at least 4 words (each word can be followed by punctuation)
        if not re.match((4 * "\w+\S*? ").rstrip(), line):
            return

        content = []
        quotes = self.searchDb(line, fetchLimit=1, matchLimit=3, exact=True)
        if quotes:
            for quote in quotes:
                content.append("%s (%s)\n" % (quote.url, quote.title))
                embed = None
                try:
                    img_url = await self.getComicImageUrl(quote.url)
                    if img_url:
                        embed = Embed()
                        embed.set_image(url=img_url)
                except Exception as e:
                    logging.exception("Error getting PA comic")
                await c.reply(content, em=embed)


    async def getComicImageUrl(self, url):
        # Needed for PA, otherwise it returns a 403
        headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0"}

        html = None
        async with ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                html = await response.read()

        if html:
            soup = BeautifulSoup(html.decode('utf-8'), 'html.parser')
            comicFrame = soup.find(id="comicFrame")
            if comicFrame:
                return comicFrame.img['src']


    @command("quotes")
    @level(2)
    @usage("!quotes <search term>")
    @desc("Searches for quotes matching the given terms.")
    async def search(self, c, args):
    
        term = ""

        try:
            term = "%s" % args.strip() 
        except ValueError:
            raise CmdParamError("Not a valid search term")
    
        content = []
        quotes = self.searchDb(term, fetchLimit=3)
        if quotes:
            for quote in quotes:
                content.append(quote.url)
        else:
            content.append("No matches")

        await c.reply(content)


    def searchDb(self, terms, fetchLimit=3, matchLimit=None, exact=False):
        text = terms.lower().strip()
        text = re.sub(r'[^a-zA-Z0-9 ]+?','', text)
        text = re.sub(r'\s+?',' ', text)
        text = text.strip()
        if exact:
            quotes = models.QuoteLink.objects.filter(match_text__icontains=text)
        else:
            quotes = models.QuoteLink.objects.filter(match_text__search=text)
        return list(quotes[:fetchLimit])


       
