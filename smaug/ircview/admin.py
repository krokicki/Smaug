from django.contrib import admin
from smaug.ircview.models import *

class SmaugUserHandleInline(admin.TabularInline):
    model = SmaugUserHandle

class IrcUserHostInline(admin.TabularInline):
    model = IrcUserHost

class SmaugUserProfileInline(admin.TabularInline):
    model = SmaugUserProfile

class SmaugUserProfileAdmin(admin.ModelAdmin):
    inlines = [ 
        SmaugUserHandleInline, 
        IrcUserHostInline
    ]

admin.site.register(SmaugUserProfile, SmaugUserProfileAdmin)


class SmaugUserAdmin(admin.ModelAdmin):
    inlines = [ 
        SmaugUserProfileInline
    ]

admin.site.register(SmaugUser, SmaugUserAdmin)


