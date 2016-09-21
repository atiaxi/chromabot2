import logging
import unittest
from configparser import ConfigParser

from chromabot2 import commands
from chromabot2.bot import Chromabot
from chromabot2.battle import Battle
from chromabot2.models import User
from chromabot2.outsiders import NullOutsider, Message
from chromabot2.utils import now


class MockConf(object):

    def __init__(self):
        self.data = ConfigParser()

        # Some sane defaults
        self['bot'] = dict()
        self.bot['dbstring'] = "sqlite://"

        self['battle'] = dict()
        self.battle['delay'] = "600"
        self.battle['time'] = "7200"
        # end_var deliberately left out
        self.battle['columns'] = "11"
        self.battle['rows'] = "5"
        # Long troop delay to prevent troops from moving unless we say so
        self.battle['troop_delay'] = "3600"
        self.battle['goal_score'] = "2"
        self.battle['kill_score'] = "1"

    def refresh(self):
        pass

    def __getitem__(self, key):
        return self.data[key]

    def __getattr__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value


class TestOutsider(NullOutsider):

    def __init__(self, override_conf=None):
        if not override_conf:
            override_conf = MockConf()
        self.provided_messages = []
        self.battle = None
        super().__init__(override_conf)

    def provide_message(self, raw_text, as_who):
        msg = Message(raw_text, as_who, self)
        self.provided_messages.append(msg)

    def get_messages(self):
        result = self.provided_messages
        self.provided_messages = []
        return result

    def infer_battle(self, message):
        if self.battle:
            return self.battle

    def populate_battle_data(self, battle, data):
        # Not setting self.battle here because some tests depend on not being
        # able to infer it.
        data['test'] = {'werg': 'hello'}


class ChromaTest(unittest.TestCase):

    def setUp(self):
        # logging.basicConfig(level=logging.DEBUG)
        logging.basicConfig(level=logging.WARN)
        self.outside = TestOutsider()
        self.bot = Chromabot(self.outside)
        self.config = self.outside.config
        self.db = self.outside.db
        self.db.create_all()
        # Region.create_from_json(self.sess, TEST_LANDS)

        # Create some users
        self.alice = User.create(self.db, "alice", team=0)
        self.bob = User.create(self.db, "bob", team=1)

        # Somewhere for them to fight
        self.battle = Battle.create(self.outside)
        self.battle.active = True

    def end_battle(self, battle=None):
        if not battle:
            battle = self.battle
        battle.ends = now()
        return self.bot_loop()

    def execute(self, message_text, *, assert_pass=True, as_who=None):
        if not as_who:
            as_who = self.alice

        self.outside.provide_message(message_text, as_who)
        results = self.bot_loop()
        if assert_pass:
            self.assertTrue(results)
            for result in results:
                msg = "Executing `%s` failed unexpectedly: %s"
                self.assertTrue(result.success,
                                msg % (message_text, result.text))
                self.assertNotEqual(result.code, commands.CODE_NOK)

        return results

    def fail_to_execute(self, message_text, *, as_who=None, err_text=None):
        results = self.execute(message_text, assert_pass=False, as_who=as_who)
        for result in results:
            msg = "`%s` succeeded unexpectedly: %s" % (message_text,
                                                       result.text)
            self.assertFalse(result.success, msg)
            if err_text:
                self.assertIn(err_text, result.text)
            self.assertEqual(result.code, commands.CODE_NOK)

    def bot_loop(self):
        return self.bot.loop_once()
