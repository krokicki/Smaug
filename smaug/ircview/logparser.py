import re
import time

MAX_URL_LENGTH = 55

COLORS = {
    0 : 'white',
    1 : 'black',
    2 : 'darkblue',
    3 : 'green',
    4 : 'red',
    5 : 'maroon',
    6 : 'purple',
    7 : 'orange',
    8 : 'yellow',
    9 : 'lime',
    10 : 'teal',
    11 : 'aqua',
    12 : 'blue',
    13 : 'fuchsia',
    14 : 'gray',
    15 : 'silver',
}

class LineParser:

    def __init__(self,colors):
        self.colors = colors

    def parseLine(self, line):

        try:
            stamp,author,text = line.split(' ',2)
            return stamp,author,text
        except ValueError:
            try:
                stamp,text = line.split(' ')
                return stamp,None,text
            except ValueError:
                return None,None,line


    def getColor(self, author, line):
        if not author:
            if line.startswith('***'):
                if line.find("sets mode") >= 0 or line.find("was kicked") >= 0:
                    return 'fuchsia'
                elif line.find("was kicked") >= 0:
                    return 'lime'
                else:
                    return 'white'
            elif line.startswith('*'):
                return 'white'
            else:
                return 'fuchsia'
        elif author[0] == '-':
            return 'lime'
        parts = author.split('|')
        handle = parts[0].lower()
        if handle in self.colors:
            return self.colors[handle]
        return ''


    def htmlizeLine(self, text):
 
        # escape existing HTML
        text = self.escape(text)

        # bold underline
        text = re.compile(r"\x02\x1f(.*?)\x0a").sub(r"<b><u>\1</u></b>", text)

        # bold
        text = re.compile(r"\x02(.*?)(\x02|\x0a)").sub(r"<b>\1</b>", text)

        # underline
        text = re.compile(r"\x1f(.*?)\x0a").sub(r"<u>\1</u>", text)

        # start color
        def subColor(m):
            g = m.groups()
            fg,bg = '',''
            if g[0]:
                color = int(g[0])
                if color in COLORS:
                    fg = "color:%s;"%COLORS[color]
            if g[2]:
                bg = "background-color:%s;"%COLORS[int(g[2])]
            return """<span style="%s%s">"""%(fg,bg)

        text = re.compile(r"\x03(\d{1,2})(,(\d{1,2}))?").sub(subColor, text)
       
        # end color
        text = re.compile(r"\x02").sub(r"</span>", text)
        text = re.compile(r"\x03").sub(r"</span>", text)
        
        # create links, break long URLs
        def subLink(m):
            label = url = m.group(1)
            if len(url) > MAX_URL_LENGTH: 
                label = "%s..."% url[:MAX_URL_LENGTH] 
            return r"""<a href="%s" target="_new">%s</a>%s"""%(url,label,m.group(2))
        text = re.compile(r"(https?://.*?)(\s|<|$)").sub(subLink, text)

        # new lines
        text = text.replace("\n", "<br />")

        # preserve spaces
        text = re.compile(r"\s\s").sub(r" &nbsp;", text)

        return text

    def formatDate(self, date):
        if not date: return ''
        formatted = date.strftime("%m/%d/%Y %H:%M%p")
        formatted.replace("AM",'a').replace("PM",'p')
        return formatted 

    def formatTimeStamp(self, date):
        if not date: return ''
        return int(time.mktime(date.timetuple()))

    def escape(self, text):
        if not text: return ''
        s = text.replace("&", "&amp;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        return s

