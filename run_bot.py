#!/usr/bin/env python

from django.conf import settings
import bot_settings
import web_settings
import re


def dict_from_module(module):
    p = re.compile("^[A-Z_]+$")
    context = {}
    for var in dir(module):
        if p.match(var):
            context[var] = getattr(module, var)
    return context


if __name__ == "__main__":

    # Merge bot settings to override web settings where necessary
    w = dict_from_module(web_settings)
    b = dict_from_module(bot_settings)
    z = {**w, **b}

    settings.configure(**z)

    import os
    os.environ.setdefault("SMAUG_SETTINGS_MODULE", "bot_settings")

    # Standalone Django app setup, needed for ORM
    import django
    django.setup()

    # Start the bot event loop
    from smaug.bot import bot
    bot.SmaugBot().run()

