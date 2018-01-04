#!/usr/bin/env python

if __name__ == "__main__":

    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_settings")
    os.environ.setdefault("SMAUG_SETTINGS_MODULE", "bot_settings")

    # Standalone Django app setup, needed for ORM
    import django
    django.setup()

    # Start the bot event loop
    from smaug.bot import bot
    bot.SmaugBot().run()

