"""
Smaug protocol base class.
Provides functions common to protocols.
"""

class Protocol(object):
    """ General plugin functions
        This is also the place to define any interfaces the protocol must implement
    """

    def __init__(self):
        self.channel = None


    def getPublicChannelNames(self):
        """ Return an iterable containing names of channels (each prepended with '#')
            which are monitored.
        """
        pass

    def die(self):
        """ Called when the entire bot is shutting down.
        """
        pass

    def sendMessage(self, where, line):
        """ Send a message to an entity (channel/user)
        """
        pass
 

    def sendNotification(self, where, line):
        """ Send a notification to an entity
        """
        pass
 

    def format(self, s, **attrib):
        """ Called by command functions to format output
            on a specific protocol.

            The given string s should for formatted according to 
            the attributes given. Attributes may be:
                color = 'colorname'
                bold = 'true'
                reverse = 'true'
                underline = 'true'
        """
        return s


    def formatSender(self, nick):
        """ Implements protocol
        """
        return "%s: " % nick

