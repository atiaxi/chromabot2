from pyparsing import *

from .battle import SkirmishCommand
from .commands import (
    # CodewordCommand,
    # DefectCommand,
    # ExtractCommand,
    # InvadeCommand,
    # MoveCommand,
    # PromoteCommand,
    StatusCommand,
    # StopCommand,
    # TimeCommand,
)


class Destination(object):
    def __init__(self, tokens):
        tok = tokens[:]  # Modifying tokens in place is bad
        self.destination = None
        self.destination_sector = 0
        if tok[0] == "*":
            self.destination = "*"
            tok.pop()
        elif tok[0] != "#":
            self.destination = tok.pop(0)
        if tok:  # Leftovers mean sectors
            tok.pop(0)  # Pop off the "#"
            self.destination_sector = int(tok.pop(0))


# http://stackoverflow.com/questions/2339386/python-pyparsing-unicode-characters
unicodePrintables = ''.join(chr(c) for c in range(65536)
                            if not chr(c).isspace())
number = Word(nums)
string = QuotedString('"', '\\')
subreddit = Suppress("/r/") + Word(alphanums + "_-")
location = string | subreddit | Word(alphanums + "_-")
eolstring = Word(unicodePrintables + " ")

attack = Keyword("attack")
oppose = Keyword("oppose")
support = Keyword("support")
participate = attack | oppose | support


target = Suppress("#") + number("target")
skirmishcmd = (Suppress(participate("action")) +
               Optional(Suppress('#') + Word(nums)("battle")) +
               Suppress("at") + Word(alphas, exact=1)("col") +
               Optional(",") + Word(nums)("row") +
               Suppress("with") + eolstring("troop_type"))

skirmishcmd.setParseAction(SkirmishCommand)

# invade = Keyword("invade")
# invadecmd = invade + location("where")
# invadecmd.setParseAction(InvadeCommand)
#
# move = Keyword("lead")
# sector ="#" + number
# destination = location + sector | location | sector | Keyword("*")
# destination.setParseAction(Destination)
# movecmd = (move + Optional(number("amount") | Keyword("all")) +
#            Suppress("to") + delimitedList(destination)("where"))
# movecmd.setParseAction(MoveCommand)
#
# extractcmd = Keyword("extract")
# extractcmd.setParseAction(ExtractCommand)
#
# stopcmd = Keyword("stop")
# stopcmd.setParseAction(StopCommand)
#
# defect = Keyword("defect")
# team = Keyword("orangered") | Keyword("periwinkle")
# defectcmd = (defect + Optional(Keyword("to") + team("team")))
# defectcmd.setParseAction(DefectCommand)
#
# promote = (Keyword("promote") | Keyword("demote"))
# promotecmd = promote("direction") + Word(alphanums + "_-")("who")
# promotecmd.setParseAction(PromoteCommand)
#
# timecmd = Keyword("time")
# timecmd.setParseAction(TimeCommand)
#
#
# removecode = Keyword("remove")('remove') + (Keyword("all")('all')
#                                             | string("code"))
# assigncode = string("code") + Keyword("is") + (alltroops("troop_type")
#                                                | string("troop_type"))
# statuscode = Keyword("status")('status') + Optional(string("code"))
# codewordcmd = Keyword("codeword") + (removecode | statuscode | assigncode)
# codewordcmd.setParseAction(CodewordCommand)
#
statuscmd = Keyword("status")
statuscmd.setParseAction(StatusCommand)
#
# root = (statuscmd | movecmd | invadecmd | skirmishcmd | defectcmd |
#         promotecmd | timecmd | codewordcmd | extractcmd | stopcmd)

root = (
    skirmishcmd |
    statuscmd
)


def parse(s):
    result = root.parseString(s.lower())
    return result[0]
