from smaug.ircview import models, logparser
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404

from django import forms

import re
import datetime
import time
import logging

logger = logging.getLogger(__name__)

PAGE_SIZE = 50 
INPUT_DATE_FORMAT= '%Y-%m-%d'
MONTHS = ('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')

class SearchForm(forms.Form):
    searchText = forms.CharField(label="Search", required=False, max_length=100)
    startDate = forms.DateField(label="From Date", required=False)
    endDate = forms.DateField(label="To Date", required=False)
    author = forms.ModelChoiceField(label="Author", required=False, queryset=models.SmaugUser.objects.all())
    proto = forms.ChoiceField(label="Protocol", required=False, choices=(('','---------'),('irc','IRC'),('discord','Discord')))
    page = forms.IntegerField(initial=0, required=False, widget=forms.HiddenInput())


@permission_required("ircview.can_view_logs")
def message(request, messageId):

    msg = get_object_or_404(models.Message, id=messageId)

    return render(request, 'message.html',{
        'msg': msg
    })


@permission_required("ircview.can_view_logs")
def index(request):

    q = models.LogLine.objects.values('year','month').distinct()

    logyears = {}
    for row in list(q): 
        if not row: break
        year = row['year'] 
        month = row['month']

        if year not in logyears:
            logyears[year] = {}

        logyears[year][MONTHS[int(month)-1]] = True

    return render(request, 'index.html',{
        'pageid' : 'index',
        'years' : sorted(logyears.items()),
        'months' : MONTHS,
        'form' : SearchForm(),
        'error' : None,
        'user' : request.user,
    })


@never_cache
@permission_required("ircview.can_view_logs")
def latest(request):

    line = None
    try:
        line = models.LogLine.objects.order_by('-stamp')[0]
    except IndexError:
        return render(request, 'results.html',{
            'pageid' : 'latest',
            'error' : "No content available",
            'user' : request.user,
        })
 
    year = line.stamp.year
    month = line.stamp.month

    q = models.LogLine.objects.filter(year=year, month=month)
    page = int(q.count() / PAGE_SIZE)

    return log(request, year, month, page=page, pageid='latest')


@never_cache
@permission_required("ircview.can_view_logs")
def tldr(request):

    days = 1
    maxLines = 100

    if 'days' in request.GET:
        try:
            days= int(request.GET['days'])
        except ValueError:
            pass
    if 'max' in request.GET:
        try:
            maxLines = int(request.GET['max'])
            if maxLines>1000: maxLines=1000
        except ValueError:
            pass

    line = None
    try:
        line = models.LogLine.objects.order_by('-stamp')[0]
    except IndexError:
        return render(request, 'results.html',{
            'pageid' : 'tldr',
            'error' : "No content available",
            'user' : request.user,
        })
 
    startDate = str(line.stamp - datetime.timedelta(hours=days*24))
    q = models.LogLine.objects
    q = q.filter(body__contains="http")
    if '.' in startDate:
        startDate = startDate[0:startDate.rfind('.')]
    q = q.extra(where=["stamp >= STR_TO_DATE(%s,'%%Y-%%m-%%d %%H:%%i:%%s')"],params=[startDate])
    q = q[0:maxLines]
    results = list(q)
    
    urls = []
    for result in results:
        for url in findUrls(result.body):
            if result.handle=='Smaug' and ('tinyurl.com' in url or 'penny-arcade' in url):
                continue
            url = url.replace('%3F','?').replace('%3D','=')
            urls.append(url)

    urls = f7(urls)
    youtubes = []
    images = []
    links = []
    for url in urls:
        if 'youtube.com/watch' in url:
            yids = findYids(url)
            if yids:
                youtubes.append(yids[0])
        elif url.lower().endswith('.gif') or url.lower().endswith('.jpg') or url.lower().endswith('.jpeg') or url.lower().endswith('.png'):
            images.append(url)
        else:
            links.append(url)

    youtube1 = None
    if youtubes: youtube1 = youtubes[0]

    return render(request, 'tldr.html',{
        'pageid' : 'tldr',
        'youtube1' : youtube1,
        'youtubes' : youtubes,
        'images' : images,
        'links' : links
    })


def f7(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]


# taken from smaug urls plugin, should be factored into a common module
def findUrls(line):
    return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line)


def findYids(url):
    return re.findall("#(?<=v=)[a-zA-Z0-9-]+(?=&)|(?<=v\/)[^&\n]+(?=\?)|(?<=v=)[^&\n]+|(?<=youtu.be/)[^&\n]+#", url) 


@permission_required("ircview.can_view_logs")
def log(request, year, month, page=0, pageid=''):

    lineId = None
    more = None

    if 'id' in request.GET:
        try:
            lineId = int(request.GET['id'])
        except ValueError:
            pass
    elif not page and 'page' in request.GET:
        try:
            page = int(request.GET['page'])
        except ValueError:
            pass

    q = models.LogLine.objects.filter(year=year, month=month).order_by('stamp')

    if lineId:
        firstId = q[0].id
        page = int((lineId - firstId) / PAGE_SIZE)

    start = page*PAGE_SIZE
    end = start+PAGE_SIZE 
    more = q.count() > end+1

    # TODO: implement paging across months

    q = q[start:end]
    results = list(q)

    parser = logparser.LineParser(getColorMap())
    for line in results:
        line.color = parser.getColor(line.handle,line.body)
        line.formattedStamp = parser.formatTimeStamp(line.stamp)
        line.formattedDate = parser.formatDate(line.stamp)
        line.htmlHandle = parser.escape(line.handle)
        line.htmlBody = parser.htmlizeLine(line.body)

    return render(request, 'results.html',{
        'pageid' : pageid,
        'results' : results,
        'more' : more,
        'page' : page,
        'year' : year,
        'month' : month,
        'anchor' : lineId,
        'error' : None,
        'user' : request.user,
    })


@permission_required("ircview.can_view_logs")
def search(request):

    form = SearchForm(request.GET)
    if not(form.is_valid()):
        return render(request, 'results.html',{
                'form': form,
                'isSearch': True,
                'users' : models.SmaugUser.objects.all(),
            })

    searchText = form.cleaned_data['searchText']
    startDate = form.cleaned_data['startDate']
    endDate = form.cleaned_data['endDate']
    author = form.cleaned_data['author']
    page = form.cleaned_data['page'] 
    proto = form.cleaned_data['proto'] 

    if not page: page = 0
    
    # reset page in the form, so that doing a new search starts on the first page
    data = form.data.copy()
    data['page'] = 0
    form = SearchForm(data)

    start = page*PAGE_SIZE
    end = start+PAGE_SIZE 

    q = models.LogLine.objects.all()
    
    if searchText:
        q = q.filter(body__search="%s"%searchText)
    
    if startDate:
        d = parseInputDate(startDate.isoformat())
        q = q.extra(where=['stamp >= DATE(%s)'], params=[d])

    if endDate:
        d = parseInputDate(endDate.isoformat())
        q = q.extra(where=['stamp <= DATE(%s)'], params=[d])

    if author:
        q = q.filter(user=author)

    if proto:
        q = q.filter(proto=proto.lower())

    more = False
    if q[start:].count() > PAGE_SIZE:
        more = True

    q = q[start:end]
    results = list(q)

    parser = logparser.LineParser(getColorMap())
    for line in results:
        line.color = parser.getColor(line.handle,line.body)
        line.formattedStamp = parser.formatTimeStamp(line.stamp)
        line.formattedDate = parser.formatDate(line.stamp)
        line.htmlHandle = parser.escape(line.handle)
        line.htmlBody = parser.htmlizeLine(line.body)

    return render(request, 'results.html',{
        'form': form,
        'results' : results,
        'more' : more,
        'page' : page,
        'anchor' : None,
        'error' : None,
        'isSearch' : True,
        'user' : request.user,
    })


# Utility functions


colorMap = {}
lastColorMapLoad = 0

def getColorMap():
    global lastColorMapLoad
    if time.time() - lastColorMapLoad > 60*30:
        # reload color map
        for user in models.SmaugUser.objects.all():
            try:
                profile = user.profile
                handles = profile.handles.all()
                for handle in handles:
                    colorMap[handle.handle.lower()] = profile.color
            except models.SmaugUserProfile.DoesNotExist:
                logger.debug("User has no profile: %s" % user.username)
                pass

        lastColorMapLoad = time.time()

    return colorMap

def parseInputDate(value):
    if not value: return None
    return datetime.datetime(*time.strptime(value, INPUT_DATE_FORMAT)[:3])

def createInputDate(date):
    if not(date): return None
    return date.strftime(INPUT_DATE_FORMAT)

