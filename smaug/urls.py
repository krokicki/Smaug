from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

from django.contrib.auth import views as auth_views
from smaug.ircview import views as ircviews
from django.views.static import serve

admin.autodiscover()

urlpatterns = [
    # admin interface
    url(r'^admin/', admin.site.urls),
    url(r'^admin/password_reset/$', auth_views.password_reset, name='admin_password_reset'),
    url(r'^admin/password_reset/done/$', auth_views.password_reset_done),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', auth_views.password_reset_confirm),
    url(r'^reset/done/$', auth_views.password_reset_complete),
    url(r'^accounts/login/$', auth_views.login),
    url(r'^accounts/logout/$', auth_views.logout_then_login, {'login_url':'/ircview/'}),

    # irc view
    url(r'^ircview/$', ircviews.index, name='index'),
    url(r'^ircview/(\d+)/(\d+)/$', ircviews.log, name='log'),
    url(r'^ircview/latest/$', ircviews.latest, name='latest'),
    url(r'^ircview/tldr/$', ircviews.tldr, name='tldr'),
    url(r'^ircview/search/$', ircviews.search, name='search'),
    url(r'^ircview/media/(?P<path>.*)$', serve, { 'document_root': settings.MEDIA_ROOT, }),
    url(r'^ircview/message/(\d+)/$', ircviews.message, name='message')
]

