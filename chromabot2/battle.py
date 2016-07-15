# All the battle related stuff that'd ordinarily go in commands or db
# goes into this file instead, because otherwise everything here just
# dwarfs everything else
import json
import logging
import random
import string
from contextlib import contextmanager

from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, Text
from sqlalchemy.orm import relationship

from .commands import (
    CODE_BEGIN_BATTLE,
    CODE_END_BATTLE,
    CODE_INFO,
    CODE_NOK,
    CODE_SCORE,
    Command,
    Result,
)
from .db import Base, ChromaException
from .utils import now, letter_to_col


# EXCEPTIONS
class OccupiedException(ChromaException):
    """Tried to put troops where something else was"""


class OutOfBoundsException(ChromaException):
    """Tried to place a troop off of the board or on the wrong side"""


class BattleExtractionException(ChromaException):
    """Whatever battle you meant, it's wrong"""


class BattleEndedException(ChromaException):
    """The battle's over, you can't do anything"""


class BattleNotStartedException(ChromaException):
    """The battle is yet to start!"""


# COMMANDS
class SkirmishCommand(Command):
    def __init__(self, tokens):
        super().__init__(tokens)
        self.raw_col = tokens['col']
        self.col = letter_to_col(self.raw_col)
        self.raw_row = tokens['row']
        self.row = max(0, int(self.raw_row) - 1)
        self.troop_type = tokens['troop_type']
        self.battle_id = 0

        if 'battle' in tokens:
            self.battle_id = int(tokens['battle'])

    def extract_battle(self, message):
        with message.outside.db.session() as s:
            if self.battle_id:
                battle = s.query(Battle).get(self.battle_id)
                if not battle:
                    msg = "Battle %d does not exist!" % self.battle_id
                    raise BattleExtractionException(msg)
                return battle

            battle = message.infer_battle()
            if battle:
                return battle

            battles = s.query(Battle).filter_by(active=True).all()
            if not battles:
                raise BattleExtractionException(
                    "There are no battles underway!")
            if len(battles) > 1:
                raise BattleExtractionException(
                    "There is more than one battle underway; you must specify "
                    "which one to participate in.")
            return battles[0]

    def execute(self, message):
        try:
            battle = self.extract_battle(message)
        except BattleExtractionException as bee:
            return Result.from_exception(bee, message)

        # Find first troop that's not already in a battle
        # and is the specified type
        chosen = None
        for troop in message.issuer.troops:
            if troop.type == self.troop_type and troop.is_deployable():
                chosen = troop
                break
        else:
            return Result(
                "Could not find any free '%s' troops" % self.troop_type,
                message,
                code=CODE_NOK,
                success=False)

        battle.place_troop(chosen, col=self.col, row=self.row,
                           outside=message.outside)

        txt = "Attacking #%d with %s at %s,%s" % (
            battle.id,
            self.troop_type,
            self.raw_col,
            self.raw_row)
        return Result(txt, message)


# DB

class Troop(Base):
    __tablename__ = 'troops'

    id = Column(Integer, primary_key=True)
    battle_id = Column(Integer, ForeignKey('battles.id'))
    battle = relationship("Battle", back_populates="troops")
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship("User", back_populates="troops")
    hp = Column(Integer)
    type = Column(String(255))
    cause_of_death = Column(Text)

    row = Column(Integer)
    col = Column(Integer)
    visible = Column(Boolean)
    opposed = Column(Boolean)
    last_move = Column(Integer)

    @classmethod
    def standard_troop(cls, troop_type, owner):
        with owner.session() as s:
            troop = cls(owner=owner, hp=1, type=troop_type, row=0, col=0,
                        visible=False, opposed=False,
                        last_move=0)
            s.add(troop)
        return troop

    @classmethod
    def infantry(cls, owner):
        return cls.standard_troop('infantry', owner)

    @classmethod
    def cavalry(cls, owner):
        return cls.standard_troop('cavalry', owner)

    @classmethod
    def ranged(cls, owner):
        return cls.standard_troop('ranged', owner)

    @property
    def team(self):
        team = getattr(self, '_team', None)
        if team is None:
            self._team = self.owner.team
            team = self._team
        return team

    def fights(self, other):
        """Returns 1 if this troop wins, 0 for a tie, and -1 for a loss"""
        if self.type == other.type:
            return 0
        ordering = ["ranged", "infantry", "cavalry"]
        our_index = ordering.index(self.type)
        win_against = ordering[our_index - 1]
        if self.type == win_against:
            return 1
        return -1

    def is_alive(self):
        return self.hp

    def is_deployable(self):
        return self.hp and not self.battle

    def icon_for_troop(self, config):
        key = "icons_%d" % self.team
        if self.visible:
            icon = config[key][self.type]
        else:
            icon = config[key]['unknown']
        # Directionality for team
        if self.team == 0:
            return "%s>" % icon
        else:
            return "<%s" % icon

    def rez(self):
        with self.session():
            self.hp = 1
            self.cause_of_death = ''
            self.visible = False
            self.opposed = False

    def __repr__(self):
        return "<Troop(type='%s', hp=%d, owner_id=%d)>" % (
            self.type, self.hp, self.owner_id)


class Battle(Base):
    __tablename__ = "battles"

    id = Column(Integer, primary_key=True)
    begins = Column(Integer, default=0)
    ends = Column(Integer, default=0)
    display_ends = Column(Integer, default=0)
    outside_data = Column(Text)  # JSON
    active = Column(Boolean)
    relevant = Column(Boolean)

    state = Column(Text)  # JSON

    victor = Column(Integer)  # -1 if nobody won this
    scores = Column(Text)  # JSON

    # region_id = Column(Integer, ForeignKey('regions.id'))
    # region = relationship("Region", backref=backref("battle", uselist=False))

    troops = relationship("Troop", back_populates="battle")

    lockout = Column(Integer, default=0)

    @classmethod
    def create(cls, outside):
        begins = now() + outside.config["battle"].getint("delay")
        display_ends = begins + outside.config["battle"].getint("time")

        # Actual ending is within end_var of the end
        chooserange = outside.config["battle"].getint("end_var", fallback=0)
        chosen = random.randint(0, chooserange)
        ends = display_ends - (chooserange / 2) + chosen

        board = []
        # NOTE: Unlike my other stuff this is ROW MAJOR.  That means I'll have
        #       to get used to board[y][x], but it just makes more sense this
        #       way (ops tend to happen in rows rather than columns)
        for y in range(outside.config["battle"].getint("rows")):
            row = []
            for x in range(outside.config["battle"].getint("columns")):
                row.append(0)  # The number in the board is the troop ID.
            board.append(row)

        state = {
            'board': board
        }
        scores = [0, 0]

        outside_data = {}

        with outside.db.session() as s:
            result = cls(begins=begins, ends=ends, display_ends=display_ends,
                         outside_data=json.dumps(outside_data),
                         state=json.dumps(state), victor=-1,
                         scores=json.dumps(scores), active=False,
                         relevant=True)
            s.add(result)

        with outside.db.session():
            with result.load_and_adopt_outside_data() as data:
                    outside.populate_battle_data(result, data)
        return result

    def place_troop(self, troop, *, col, row, outside, moving=False):
        battle_report = ''
        board = self.load_board()
        if not moving:
            if not self.active:
                # Which end is it?
                if now() >= self.ends:
                    raise BattleEndedException("That battle is over!")
                elif now() < self.begins:
                    raise BattleNotStartedException(
                        "That battle has not yet begun!")
                else:
                    raise BattleEndedException(
                        "That battle has ended early!")
            if row < 0 or row >= len(board):
                raise OutOfBoundsException("That row is not on the board!")
            if col < 0 or col >= len(board[0]):
                    raise OutOfBoundsException(
                        "That column is not on the board!")
            if troop.team == 0 and col >= len(board[0]) // 2:
                raise OutOfBoundsException(
                    "You cannot place a troop in enemy territory")
            elif troop.team == 1 and col <= len(board[0]) // 2:
                raise OutOfBoundsException(
                    "You cannot place a troop in enemy territory")
            if board[row][col]:
                raise OccupiedException(
                    "There is already a troop at that location")
            with self.session():
                troop.battle = self
        else:
            # Ephemeral
            troop.moved = False
            if col < 0 or col >= len(board[0]):
                # SCORE!
                self.kill_troop(troop, "is behind enemy lines")
                with self.load_and_adopt_scores() as scores:
                    amount = outside.config.battle.getint('goal_score')
                    if not troop.opposed:
                        amount *= 2
                    scores[troop.team] = scores[troop.team] + amount
                    result = Result(
                        "Troop %d slipped behind enemy lines, awarding "
                        "team %d %d points" % (troop.id, troop.team, amount),
                        code=CODE_SCORE,
                        extra={'team': troop.team, 'amount': amount})
                    return result

            if board[row][col]:
                with self.session() as s:
                    other = s.query(Troop).get(board[row][col])
                if troop.team == other.team:
                    return Result(
                        "Troop %d halted to avoid friendly fire" % troop.id,
                        code=CODE_INFO)
                # Oh shit, FIGHT!
                windex = troop.fights(other)
                winner = [None, troop, other][windex]
                loser = [None, other, troop][windex]
                if winner:
                    winner.opposed = True
                    winner.visible = True
                    self.kill_troop(loser, "has fallen in battle")
                    with self.load_and_adopt_scores() as scores:
                        amount = outside.config.battle.getint('kill_score')
                        scores[winner.team] = scores[winner.team] + amount
                    if winner == troop:
                        battle_report = ": defeated %d" % loser.id
                    else:
                        battle_report = ": was defeated by %d" % winner.id
                else:
                    self.evict_troop(troop)
                    self.evict_troop(other)
                    battle_report = ": tied with %d" % other.id

        if troop.battle:
            with self.session():
                troop.col = col
                troop.row = row
                troop.last_move = now()
                with self.load_and_adopt_board() as board:
                    board[row][col] = troop.id
                troop.moved = True

            verb = "placed at"
            if moving:
                verb = "moved to"
            txt = "Troop %d %s row %d, col %d%s" % (troop.id, verb,
                                                    troop.row, troop.col,
                                                    battle_report)
            return Result(txt, code=CODE_INFO)
        return Result("Troop %d left the field%s" % (troop.id, battle_report),
                      code=CODE_INFO)

    def move_troop(self, troop, outside):
        direction = [1, -1][troop.team]
        # TODO: Check to see if there's anything in the way
        row = troop.row
        col = troop.col
        newcol = col + direction
        result = self.place_troop(troop, col=newcol, row=row, moving=True,
                                  outside=outside)
        if troop.moved:
            with self.session():
                with self.load_and_adopt_board() as board:
                    board[row][col] = 0

        return result

    def kill_troop(self, troop, cause_of_death):
        with self.session():
            # troop.battle = None
            troop.cause_of_death = cause_of_death
            troop.hp = 0
            with self.load_and_adopt_board() as board:
                board[troop.row][troop.col] = 0

    def evict_troop(self, troop, clear_board=True):
        troop.rez()
        with self.session():
            troop.battle = None
            if clear_board:
                with self.load_and_adopt_board() as board:
                    board[troop.row][troop.col] = 0

    def load_board(self):
        state = json.loads(self.state)
        board = state['board']
        return board

    def adopt_board(self, new_board):
        state = json.loads(self.state)
        state['board'] = new_board
        self.state = json.dumps(state)

    @contextmanager
    def load_and_adopt_board(self):
        board = self.load_board()
        yield board
        self.adopt_board(board)

    def load_scores(self):
        return json.loads(self.scores)

    def adopt_scores(self, new_scores):
        self.scores = json.dumps(new_scores)

    @contextmanager
    def load_and_adopt_scores(self, commit=True):
        scores = self.load_scores()
        yield scores
        if commit:
            with self.session():
                self.adopt_scores(scores)
        else:
            self.adopt_scores(scores)

    def load_outside_data(self):
        return json.loads(self.outside_data)

    def adopt_outside_data(self, data):
        self.outside_data = json.dumps(data)

    @contextmanager
    def load_and_adopt_outside_data(self):
        data = self.load_outside_data()
        yield data
        self.adopt_outside_data(data)

    def realize_board(self):
        state = json.loads(self.state)
        board = state['board']
        realized = []
        for row in board:
            real_row = []
            for col in row:
                if col == 0:
                    real_row.append(None)
                else:
                    with self.session() as s:
                        troop = s.query(Troop).get(col)
                        real_row.append(troop)
            realized.append(real_row)
        return realized

    def start(self):
        with self.session():
            self.active = True

    def end(self):
        scores = self.load_scores()
        victor = -1
        if scores[0] > scores[1]:
            victor = 0
        elif scores[1] > scores[0]:
            victor = 1

        with self.session():
            self.active = False
            self.victor = victor
            self.relevant = False

            for troop in self.troops[:]:
                troop.battle = None
                troop.rez()

    def update(self, outside):
        results = []
        begin = now()
        if not self.active:
            if begin >= self.begins:
                # Let's do this!
                self.start()
                res = Result("Battle %d has begun" % self.id,
                             code=CODE_BEGIN_BATTLE, extra=self)
                results.append(res)
        else:
            troop_delay = outside.config.battle.getint("troop_delay")

            for troop in self.troops[:]:
                if not troop.is_alive():
                    continue
                next_move = troop.last_move + troop_delay
                if next_move <= begin:
                    results.append(self.move_troop(troop, outside))

            if begin >= self.ends:
                msg = Result("Battle %d has completed" % self.id,
                             code=CODE_END_BATTLE,
                             extra=self)
                self.end()
                results.append(msg)
                outside.report_battle_end(self)
            else:
                outside.update_battle(self)
        return results
