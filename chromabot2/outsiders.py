import math
import readline
import string

from .db import DB
from chromabot2.battle import Battle
from chromabot2.models import User

all_outsiders = {}


def outsider(name):
    def wrap(cls):
        all_outsiders[name] = cls
        return cls
    return wrap


class Message:

    def __init__(self, raw_text, issuer, outside):
        self.raw_text = raw_text
        self.issuer = issuer
        self.outside = outside

    def __repr__(self):
        return "Message(raw_text='%s', issuer='%s')" % (self.raw_text,
                                                        self.issuer.name)

    def infer_battle(self):
        return self.outside.infer_battle(self)


class NullOutsider:

    def __init__(self, config):
        self.config = config
        self.db = DB(self.config)

    def get_messages(self):
        return []

    def handle_recruits(self):
        return []

    def infer_battle(self, message):
        # Sometimes, context can tell you what battle this is referring to.
        # But you can't get context except via an Outsider
        return None

    def populate_battle_data(self, battle, data):
        # Update the `data` dict passed in and it'll be adopted by the battle
        # in the `outside_data` field.  Convention is that `data` is a dict
        # of dicts.  The outer keys are the name of the outsider this data
        # is relevant for (to allow multiple outsiders to coexist), and the
        # inner keys are entiely arbitrary.
        pass

    def report_results(self, results):
        pass

    def startup(self):
        return []

    def status_for(self, user):
        return ""

    def visual_state(self, battle):
        return ''

    def icon_for_troop(self, troop):
        if troop:
            return troop.icon_for_troop(self.config)
        else:
            return '. '


@outsider("debug")
class DebugOutsider(NullOutsider):

    def __init__(self, config):
        super().__init__(config)
        with self.db.session() as s:
            self.battle = s.query(Battle).first()
        if not self.battle:
            self.battle = Battle.create(self)
        self.battle.start()
        self._me = None

    def get_messages(self):
        print("\n")
        print("In command loop; enter your commands.")
        print("Enter an empty line when done")

        messages = []
        message = "x"
        while message:
            try:
                message = input("DEBUG> ")
                if message:
                    if message[0] == '#':
                        self.handle_debug_message(message)
                        continue
                    msg = Message(message, self.me, self)
                    messages.append(msg)
            except EOFError:  # Ctrl-D will cause this one
                return None
        return messages

    def handle_debug_message(self, message):
        msg = message[1:].lower()
        if msg == 'exit':
            raise SystemExit
        if msg[:7] == 'become ':
            target = msg[7:]
            with self.db.session() as s:
                user = s.query(User).filter_by(name=target).first()
                if user:
                    print("Okay, you are now %s" % user.name)
                    self._me = user
                else:
                    print("I don't know who that is")

    @property
    def me(self):
        if not self._me:
            with self.db.session() as s:
                self._me = s.query(User).get(1)
        return self._me

    def report_results(self, results):
        print("The following results happen:")
        for result in results:
            if result.is_internal():
                print("INTERNAL: %s" % result.text)
            else:
                print("%s: %s" % (result.message.issuer.name, result.text))
        print("\n")
        if self.battle:
            print("The state of the board is:")
            print(self.visual_state(self.battle))

    def status_for(self, user):
        result = ["%r" % user, "Troops:"]
        result.extend(("  %r" % troop) for troop in user.troops)
        return "\n".join(result)

    def visual_state(self, battle):
        board = battle.realize_board()
        num_cols = len(board[0])
        num_rows = len(board)
        row_space = int(math.log10(num_rows)) + 1
        row_spaces = ' ' * row_space
        col_labels = [string.ascii_uppercase[i] for i in range(num_cols)]
        lines = []
        lines.append("%s%s" % (row_spaces, " ".join(col_labels)))
        for row_number, row in enumerate(board):
            # Thanks, https://pyformat.info/ !
            label = '{:<{}d}'.format(row_number+1, row_space)
            cols = [self.icon_for_troop(troop) for troop in row]
            lines.append("%s%s" % (label, "".join(cols)))
        return "\n".join(lines)
