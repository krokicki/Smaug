"""
Interface to Google search through a Custom Search
"""

from apiclient.discovery import build

from smaug.bot import settings
from smaug.bot.command import *

class Google(Plugin):
    
    def __init__(self):
        self.service = build("customsearch", "v1", developerKey=settings.GOOGLE_DEVELOPER_KEY)


    @command("google")
    @level(2)
    @usage("!google <search terms>")
    @desc("Run a Google search and return the first result.")
    async def search(self, c, args):        

        if not(args.strip()): raise CmdParamError
            
        res = self.service.cse().list(q=args,cx=settings.GOOGLE_CUSTOM_SEARCH_CX,num=1).execute()

        if not res or not('items' in res) or len(res['items'])<1:
            raise CmdExeError("Google not responding")

        if not('items' in res):
            await c.reply("No hits")
            return
   
        result = res['items'][0]
        hits = res['searchInformation']['totalResults']

        url = result['link']
        if 'htmlTitle' in result:
            title = result['htmlTitle']
        elif 'title' in result:
            title = result['title']
        else:
            title = "Unknown"
        title = self.formatHtml(c, title)
        await c.reply("%s hits; %s : %s" % (hits,
            c.protocol.format(url,color='fuchsia'),
            c.protocol.format(title, color='lime')))


    def formatHtml(self, c, html):
        html = html.replace("&amp;",'&')
        html = html.replace("&lt;",'<')
        html = html.replace("&gt;",'>')
        html = html.replace("&quot;",'"')
        p = re.compile(r"<b>(.*?)</b>")
        #html = p.sub(c.protocol.format(r"\1",bold=''),html)
        # this doesn't seem to work anymore, so let's just get rid of bold:
        html = p.sub(r"\1",html)
        return html
       



