AUTHOR = 'krokicki'
BOT_NAME = 'Smaug'
DESCRIPTION = '''
    My armour is like tenfold shields, my teeth are swords, my claws spears, the
    shock of my tail a thunderbolt, my wings a hurricane, and my breath death!
    '''
VERSION = 5.0
PROTOCOLS = ('irc','discord',)

IRC_NICK = '<CUSTOMIZE>'
IRC_PASSWORD = '<CUSTOMIZE>'
IRC_SERVER = '<CUSTOMIZE>'
IRC_PORT = 6667
IRC_CHANNELS = ('<CUSTOMIZE>',)
IRC_QUIT_MESSAGES = (
    "I kill where I wish and none dare resist.",
    "Well, thief! Come along! Help yourself again, this is plenty and to spare!",
    "Don't let your imagination run away with you!",
    "Let me tell you I ate six ponies last night...",
    "If you get off alive, you will be lucky.",
    "Ha! Ha!",
    "Revenge! The King under the Mountain is dead and where are his kin that dare seek revenge?",
    "I have eaten these people like a wolf among sheep.",
    "I laid low the warriors of old and their like is not in the world today.",
    "I am old and strong, strong, strong.",
    "Your information is antiquated.",
    "I am armored above and below with iron scales and hard gems. No blade can pierce me.",
    "They shall see me and remember who is the real King under the Mountain!",
)
IRC_LOGDIR = 'logs/irc'
IRC_MODULES = (
    'google',
    'logs',
    'messages',
    'quotelink',
    'poll',
    'rps',
    'urls',
    'users',
    'youtube',
    'tunnels'
)

DISCORD_TOKEN = "<CUSTOMIZE>"
DISCORD_SERVER_NAME = '<CUSTOMIZE>'
DISCORD_CHANNELS = ('#general',)
DISCORD_LOGDIR = 'logs/discord'
DISCORD_MODULES = (
    'google',
    'logs',
    'messages',
    'quotelink',
    'poll',
    'rps',
    'urls',
    'users',
    'youtube',
    'tunnels'
)

ACCESS_NEEDS_AUTH = 3

WEB_BASE_URL="http://<CUSTOMIZE>/ircview"

GOOGLE_DEVELOPER_KEY="<CUSTOMIZE>"
GOOGLE_CUSTOM_SEARCH_CX="<CUSTOMIZE>"

