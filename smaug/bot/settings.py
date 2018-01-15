import os
import logging
from importlib import import_module

logger = logging.getLogger(__name__)

settings_module_name = os.environ.get("SMAUG_SETTINGS_MODULE", "bot_settings")
logger.info("Smaug Bot, using settings '%s'" % settings_module_name)
settings_module = import_module(settings_module_name)

AUTHOR = settings_module.AUTHOR
BOT_NAME = settings_module.BOT_NAME
DESCRIPTION = settings_module.DESCRIPTION
VERSION = settings_module.VERSION
PROTOCOLS = settings_module.PROTOCOLS

IRC_NICK = settings_module.IRC_NICK
IRC_PASSWORD = settings_module.IRC_PASSWORD
IRC_SERVER = settings_module.IRC_SERVER
IRC_PORT = settings_module.IRC_PORT
IRC_CHANNELS = settings_module.IRC_CHANNELS
IRC_QUIT_MESSAGES = settings_module.IRC_QUIT_MESSAGES
IRC_LOGDIR = settings_module.IRC_LOGDIR
IRC_MODULES = settings_module.IRC_MODULES

DISCORD_TOKEN = settings_module.DISCORD_TOKEN
DISCORD_SERVER_NAME = settings_module.DISCORD_SERVER_NAME
DISCORD_CHANNELS = settings_module.DISCORD_CHANNELS
DISCORD_LOGDIR = settings_module.DISCORD_LOGDIR
DISCORD_MODULES = settings_module.DISCORD_MODULES
DISCORD_ALERTS = settings_module.DISCORD_ALERTS

ACCESS_NEEDS_AUTH = settings_module.ACCESS_NEEDS_AUTH

WEB_BASE_URL = settings_module.WEB_BASE_URL

GOOGLE_DEVELOPER_KEY = settings_module.GOOGLE_DEVELOPER_KEY
GOOGLE_CUSTOM_SEARCH_CX = settings_module.GOOGLE_CUSTOM_SEARCH_CX



