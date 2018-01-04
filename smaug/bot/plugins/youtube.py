"""
Interface to Youtube search 
"""

from apiclient.discovery import build

from smaug.bot import settings
from smaug.bot.command import *
from smaug.utils.urls import findUrls, findYoutubeIds

class Youtube(Plugin):
    
    def __init__(self):
        self.service = build("youtube", "v3", developerKey=settings.GOOGLE_DEVELOPER_KEY)


    @listen("hear")
    async def hear(self, c, line):
        for url in findUrls(line):
            if 'youtube.com/watch' in url:
                await self.showYoutubeUrlMetadata(c, url)


    @command("youtube")
    @level(2)
    @usage("!youtube <youtube url>")
    @desc("Return metadata about the given youtube video.")
    async def showYoutubeUrlMetadata(self, c, videoUrl):
        yids = findYoutubeIds(videoUrl)
        if not yids: return
        for yid in yids:
            await self.showYoutubeIdMetadata(c, yid)
       

    async def showYoutubeIdMetadata(self, c, videoId):
        res = self.service.videos().list(id=videoId,part="snippet,statistics",\
            fields="items(snippet(title,channelTitle),statistics)").execute()
        if not res or (not 'items' in res) or len(res['items'])<1: return
        result = res['items'][0]
        author = c.protocol.format(result['snippet']['channelTitle'], color='gray')
        
        title = result['snippet']['title']

        stats = result['statistics']

        if ('likeCount' in stats) and ('dislikeCount' in stats):
            likes = int(result['statistics']['likeCount'] or 0)
            dislikes = int(result['statistics']['dislikeCount'] or 0)
            likesStr = c.protocol.format("%d"%likes, color='lime')
            dislikesStr = c.protocol.format("%d"%dislikes, color='red')
            await c.reply("%s [%s] Likes:%s/%s" % (title,author,likesStr,dislikesStr))
        else:
            await c.reply("%s [%s]"  % (title,author))


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
       
