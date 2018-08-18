"""
Rock Paper Scissors

A simple version of rock paper scissors. A duel can be started in a channel using !rps and then the !throw's 
should come in private messages. All the output will go to the channel the game was started in.

Uses the database for tracking game statistics in the rps table.
"""

from smaug.bot.command import *
from smaug.ircview import models

from time import time

class RPS(Plugin):

    def __init__(self):
        self.rps = {}

        self.throws = {
            'r': {
                'code': 'r',
                'name': 'rock',
                'actions': {
                    's':'crushes',
                    'l':'crushes'
                }
            },
            'p': {
                'code': 'p',
                'name': 'paper',
                'actions': {
                    'r':'covers',
                    'v':'disproves'
                }
            },
            's': {
                'code': 's',
                'name': 'scissors',
                'actions': {
                    'p':'cut',
                    'l':'decapitates'
                }
            },
            'v': {
                'code': 'v',
                'name': 'Spock',
                'actions': {
                    'r':'vaporizes',
                    's':'smashes'
                }
            },
            'l': {
                'code': 'l',
                'name': 'lizard',
                'actions': {
                    'v':'poisons',
                    'p':'eats'
                }
            }
        }

        self.gambits = {
            'rrr': "Avalanche",
            'ppp': "Bureaucrat",
            'psr': "Crescendo",
            'rsp': u"D\xe9nouement",
            'rpp': "Fistfull o' Dollars",
            'pss': "Paper Dolls",
            'psp': "Scissor Sandwich",
            'sss': "Toolbox",
        }
 
    @command("rpssl")
    @level(2)
    @usage("!rpssl <opponent>")
    @desc("Challenge someone to a game of Rock Paper Scissors Spock Lizard.")
    async def startRPSSLGame(self, c, args):         
        await self.startGame(c, args, allowVL=True)

    @command("rps")
    @level(2)
    @usage("!rps <opponent>")
    @desc("Challenge someone to a game of Rock Paper Scissors.")
    async def startGame(self, c, args, allowVL=False):
        
        cmd = c.protocol.cmd

        opponent = args.strip()
        if not opponent: raise CmdParamError
        
        # check if match is in progress
        if self.rps:
            delay = time() - self.rps['time']
            if delay < 30:
                await c.reply("There is a match in progress")
                return
            
        channel = ""
        
        try:
            tproto, target = opponent.split(":",1)
            targetProtocol = cmd.getProtocol(tproto)
        except ValueError:
            # this is a public game
            channel = c.channel
            target = opponent
            targetProtocol = c.protocol

        opponentUser = cmd.getUserByHandle(target)
        
        if not opponentUser:
            await c.reply("Opponent must be a user")
            return
            
        currTime = time()
        oc = CommandContext(targetProtocol, channel, opponentUser, target, currTime)
        
        self.rps = {
            'channel': channel,
            'time': currTime,
            'games': 3,
            'game': 1,
            'games_played': 0,
            'win1': '',
            'win2': '',
            'win3': '',
            'winner': '',
            'allowVL': allowVL,
            c.user.id: { 
                'context': c,
                'opponent': opponentUser.id, 
                1: None,
                2: None,
                3: None,
                'time': 0,
                'lasttime': currTime,
            },
            opponentUser.id: { 
                'context': oc,
                'opponent': c.user.id,
                1: None,
                2: None,
                3: None,
                'time': 0,
                'lasttime': currTime,
            },
        }

        msg = "Match started: %s vs %s" % (c.user.name, opponentUser.name)

        await c.reply(msg)
        if not channel:
            await oc.reply(msg)

    @command("throw")
    @level(2)
    @usage("!throw <r[ock] | p[paper] | s[cissors] | v[spock] | l[izard]>")
    @desc("Throw your hand. You can use abbreviations if you wish. t is advised to use a private message to run this command.")
    async def RPSThrow(self, c, args):

        cmd = c.protocol.cmd

        code = args.strip().lower()
        if code == "rock" or code == "r":
            code = "r"
        elif code == "paper" or code == "p":
            code = "p"
        elif code == "scissors" or code == "s":
            code = "s"
        elif code == "spock" or code == "v":
            code = "v"
        elif code == "lizard" or code == "l":
            code = "l"
        else:
            raise CmdParamError
        
        if not(c.user.id in self.rps):
            await c.reply("You are not dueling! Use !rps to start a duel.")
            return
         
        if not(self.rps['allowVL']) and (code == 'v' or code == 'l'):
            await c.reply("You are not playing Rock Paper Scissors Spock Lizard. Use !rpssl next time.")

        mid = c.user.id
        me = self.rps[mid]
        oid = me['opponent']
        game = self.rps['game'] 
        opponent = self.rps[oid]
        channel = self.rps['channel']
        cc = me['context']
        oc = opponent['context']
        
        # play my hand
        me[game] = code
        elapsed = time() - me['lasttime']
        me['time'] += elapsed 

        if opponent[game]:
            # both hands thrown, process game
            w = '' # default is a tie
         
            # describes the throws and actions of each player
            thrown = {
                mid: self.throws[me[game]],
                oid: self.throws[opponent[game]]
            }
 
            if opponent[game] in thrown[mid]['actions']:
                w = mid
            elif me[game] in thrown[oid]['actions']:
                w = oid

            if not w:
                enemy = cmd.getUser(oid)
                msg = "%s and %s both threw %s." % \
                    (c.user.name, enemy.name, thrown[mid]['name'])
                # reset this game since it was a tie
                me[game] = ''
                opponent[game] = ''
            else:
                self.rps['win'+str(game)] = w
                
                # determine loser
                if w == mid: l = oid
                else: l = mid
                
                winnar = cmd.getUser(w)
                loser = cmd.getUser(l)

                wincode = thrown[w]['code']
                losecode = thrown[l]['code']

                msg = "%s's %s %s %s's %s" % \
                    (winnar.name, thrown[w]['name'], thrown[w]['actions'][losecode],
                    loser.name, thrown[l]['name'])
                
                self.rps['game'] += 1
        
            self.rps['games_played'] += 1
        
            if msg:
                await cc.reply(msg)
                if not channel:
                    await oc.reply(msg)
        
        if self.rps['game'] > self.rps['games']:
            # set is over, process winner
           
            wins = { mid: [], oid: [] }
            for g in range(1,self.rps['games'] + 1):
                winner = self.rps['win'+str(g)]
                if winner: wins[winner].append(g)
        
            if len(wins[mid]) > len(wins[oid]):
                winnar = cmd.getUser(mid)
                loser = cmd.getUser(oid)
            else:
                winnar = cmd.getUser(oid)
                loser = cmd.getUser(mid)
            
            wonGames = len(wins[winnar.id])
            totalGames = self.rps['games']
            
            # determine gambit
            winnerMap = self.rps[winnar.id]
            loserMap = self.rps[loser.id]
            winnerGambit = "%s%s%s" % (winnerMap[1],winnerMap[2],winnerMap[3])
            loserGambit = "%s%s%s" % (loserMap[1],loserMap[2],loserMap[3])
            withGambit = ""
            if winnerGambit in self.gambits:
                withGambit = " using the %s gambit" % self.gambits[winnerGambit]
            
            # perfect set?
            withPerfect = ""
            if wonGames == totalGames:
                withPerfect = " FLAWLESS VICTORY!"
 
            msg = "%s won the set with %s/%s%s.%s" % \
                (winnar.name, len(wins[winnar.id]), self.rps['games'],
                withGambit, withPerfect)

            if msg:
                await cc.reply(msg)
                if not channel:
                    await oc.reply(msg)

            r = models.RpsGame(winner=winnar, winner_play=winnerGambit, winner_time=winnerMap['time'],
                    loser=loser, loser_play=loserGambit, loser_time=loserMap['time'], rounds=self.rps['games_played'])
            r.save()

            # reset the game
            self.rps = {}
            
