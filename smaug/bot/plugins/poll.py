"""
Polling functions
"""

from smaug.bot.command import *

ANSWERS = {
    0: 'No',
    1: 'Yes',
}

class Poll(Plugin):

    def __init__(self):
        self.polls = {}
        self.nextPollId = 1

    @command("poll")
    @level(20)
    @usage("!poll <question>")
    @desc("Construct a new poll.")
    async def newPoll(self, c, args):

        try:
            question = args.strip()
        except ValueError:
            raise CmdParamError

        pid = self.nextPollId
        self.nextPollId += 1
        self.polls[pid] = {
            'q' : question,    
            'votes': {},
        }

        await c.reply("Poll %d started: %s Type !vote %d <yes/no> to vote."%(pid,question,pid))


    @command("vote")
    @level(2)
    @usage("!vote <poll id> [answer id]")
    @desc("Vote on the given poll.")   
    async def vote(self, c, args):
 
        try:
            poll,answer = args.split(" ",1)
            pid = int(poll)
            answer = answer.strip().lower()
            if answer == 'yes':
                aid = 1
            elif answer == 'no':
                aid = 0
            else:
                await c.reply("Answer must be 'yes' or 'no'.")
                return
        except ValueError:
            raise CmdParamError       

        if pid not in self.polls:
            await c.reply("There is no such poll.")
            return

        if c.user.id in self.polls[pid]['votes']:
            await c.reply("You have already voted in this poll.")
            return

        self.polls[pid]['votes'][c.user.id] = aid
        await c.reply("In the poll '%s', you voted %s."%(self.polls[pid]['q'],ANSWERS[aid]))


    @command("tally")
    @level(20)
    @usage("!tally <poll id>")
    @desc("Show the current tally for a poll.")
    async def showTally(self, c, args):
        
        try:
            pid = int(args)
        except ValueError:
            raise CmdParamError
 
        if pid not in self.polls:
            await c.reply("There is no such poll.")
            return

        votes = self.polls[pid]['votes']

        tally = {}
        
        for userId in list(votes.keys()):
            vote = votes[userId]
            if vote in tally:
                tally[vote] += 1
            else:
                tally[vote] = 1
        
        content = ["Poll: %s"%self.polls[pid]['q']]
        
        for vote in list(tally.keys()):
            content.append("%s: %d votes" % (ANSWERS[vote],tally[vote]))

        await c.reply(content)


