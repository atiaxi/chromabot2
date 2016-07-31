
from chromabot2.models import User
from chromabot2.battle import (
    Battle,
    Troop,
    OccupiedException,
    OutOfBoundsException,
    BattleEndedException,
    BattleNotStartedException,
)
from chromabot2.utils import now
from test.common import ChromaTest

# These tests are for the raw functionality of db.py - unit tests, mostly.
# Integration tests will be elsewhere (test_battle.py for battle related
# items, and test_play.py for most everything else)


class TestUser(ChromaTest):

    def test_create_user(self):
        someone = User.create(self.db, name="someone", team=0, leader=True)
        some_id = someone.id

        with self.db.new_session() as s:
            fetched = s.query(User).filter_by(name="someone").first()
            self.assertTrue(fetched)
            self.assertEqual(fetched.id, some_id)

            # TODO: Check to see if the user is in that team's capital

            # Make sure it assigned troops
            self.assertTrue(fetched.troops)
            self.assertEqual(3, len(fetched.troops))
            counts = {'infantry': 0, 'cavalry': 0, 'ranged': 0}
            for troop in fetched.troops:
                self.assertIn(troop.type, counts)
                counts[troop.type] += 1
            for key in counts.keys():
                self.assertEqual(1, counts[key])

    # def test_create_user_other_team(self):
    #     # someone = User.create(self.db, name="someone", team=1, leader=True)
    #     self.skipTest("No regions yet")
    #     # TODO: Check to see if the user is in the other team's capital

    def test_troops(self):
        num_troops = len(self.alice.troops)
        troop = Troop(owner=self.alice, hp=1, type="test")
        with self.db.session() as s:
            s.add(troop)

        self.assertEqual(num_troops + 1, len(self.alice.troops))
        self.assertIn(troop, self.alice.troops)


class TestTroop(ChromaTest):

    def test_owner(self):
        troop = Troop(owner=self.alice, hp=1, type="test")
        with self.db.session() as s:
            s.add(troop)

        with self.db.new_session() as s:
            fetched = s.query(Troop).\
                filter_by(type="test").first()
            self.assertTrue(fetched)
            self.assertEqual(fetched.type, troop.type)
            self.assertEqual(fetched.id, troop.id)

            self.assertEqual(fetched.owner.id, self.alice.id)

    def test_boilerplate(self):
        Troop.infantry(self.alice)

        with self.db.new_session() as s:
            fetched = s.query(Troop). \
                filter_by(type="infantry"). \
                filter_by(owner_id=self.alice.id).count()
            self.assertEqual(2, fetched)

    def test_boilerplate_cavalry(self):
        Troop.cavalry(self.alice)

        with self.db.new_session() as s:
            fetched = s.query(Troop). \
                filter_by(type="cavalry"). \
                filter_by(owner_id=self.alice.id).count()
            self.assertEqual(2, fetched)

    def test_boilerplate_ranged(self):
        Troop.ranged(self.alice)

        with self.db.new_session() as s:
            fetched = s.query(Troop). \
                filter_by(type="ranged"). \
                filter_by(owner_id=self.alice.id).count()
            self.assertEqual(2, fetched)

    def test_no_battle(self):
        troop = Troop(owner=self.alice, hp=1, type="test")
        with self.db.session() as s:
            s.add(troop)
        # By default, this troop shouldn't have a battle assigned to it
        self.assertFalse(troop.battle)

    def test_circ(self):
        # This is going to get exponential real quick but OH WELL
        cavalry = Troop.cavalry(self.alice)
        infantry = Troop.infantry(self.alice)
        ranged = Troop.ranged(self.alice)

        with self.subTest("Cavalry"):
            with self.subTest("CI"):
                self.assertEqual(cavalry.fights(infantry), 1)
            with self.subTest("RC"):
                self.assertEqual(cavalry.fights(ranged), -1)
            with self.subTest("CC"):
                self.assertEqual(cavalry.fights(cavalry), 0)

        with self.subTest("Infantry"):
            with self.subTest("IR"):
                self.assertEqual(infantry.fights(ranged), 1)
            with self.subTest("CI"):
                self.assertEqual(infantry.fights(cavalry), -1)
            with self.subTest("II"):
                self.assertEqual(infantry.fights(infantry), 0)

        with self.subTest("Ranged"):
            with self.subTest("RC"):
                self.assertEqual(ranged.fights(cavalry), 1)
            with self.subTest("IR"):
                self.assertEqual(ranged.fights(infantry), -1)
            with self.subTest("RR"):
                self.assertEqual(ranged.fights(ranged), 0)


class TestBattle(ChromaTest):

    def test_create(self):
        with self.db.session() as s:
            num_battles = s.query(Battle).count()

        battle = Battle.create(self.outside)
        self.assertTrue(battle)
        with self.db.new_session() as s:
            now_battles = s.query(Battle).count()
            self.assertEqual(num_battles+1, now_battles)

    def test_place_troop(self):
        troop = self.alice.troops[0]
        self.assertFalse(troop.battle)
        self.assertEqual(len(self.battle.troops), 0)
        self.battle.place_troop(troop, col=1, row=2, outside=self.outside)
        self.assertTrue(troop.battle)
        self.assertEqual(len(self.battle.troops), 1)
        self.assertEqual(self.battle, troop.battle)
        self.assertEqual(troop.row, 2)
        self.assertEqual(troop.col, 1)
        # Hopefully this won't take 10 minutes to run
        self.assertAlmostEqual(now(), troop.last_move, delta=600)
        board = self.battle.realize_board()
        self.assertEqual(board[troop.row][troop.col], troop)

    def test_no_place_troop_in_occupied_space(self):
        troop = self.alice.troops[0]
        self.assertEqual(len(self.battle.troops), 0)
        self.battle.place_troop(troop, col=1, row=2, outside=self.outside)

        self.assertEqual(len(self.battle.troops), 1)

        with self.assertRaises(OccupiedException):
            troop = self.alice.troops[1]
            self.battle.place_troop(troop, col=1, row=2, outside=self.outside)

        self.assertEqual(len(self.battle.troops), 1)
        self.assertFalse(self.alice.troops[1].battle)

    def test_place_troop_on_right_side_zero(self):
        for col in range(0, 5):
            troop = self.alice.troops[0]
            self.battle.place_troop(troop, col=col, row=2, outside=self.outside)
            self.assertEqual(troop.col, col)

    def test_place_troop_on_right_side_one(self):
        for col in range(6, 11):
            troop = self.bob.troops[0]
            self.battle.place_troop(troop, col=col, row=2, outside=self.outside)
            self.assertEqual(troop.col, col)

    def test_no_place_troop_on_wrong_side_zero(self):
        troop = self.alice.troops[0]
        self.assertEqual(len(self.battle.troops), 0)
        with self.assertRaises(OutOfBoundsException):
            self.battle.place_troop(troop, col=9, row=2, outside=self.outside)

        self.assertEqual(len(self.battle.troops), 0)
        self.assertFalse(self.alice.troops[0].battle)

    def test_no_place_troop_on_wrong_side_one(self):
        troop = self.bob.troops[0]
        self.assertEqual(len(self.battle.troops), 0)
        with self.assertRaises(OutOfBoundsException):
            self.battle.place_troop(troop, col=1, row=2, outside=self.outside)

        self.assertEqual(len(self.battle.troops), 0)
        self.assertFalse(self.bob.troops[0].battle)

    def test_no_place_troop_in_dmz(self):
        with self.assertRaises(OutOfBoundsException):
            troop = self.alice.troops[0]
            self.battle.place_troop(troop, col=5, row=2, outside=self.outside)

        with self.assertRaises(OutOfBoundsException):
            troop = self.bob.troops[0]
            self.battle.place_troop(troop, col=5, row=2, outside=self.outside)

    def test_no_place_troop_off_board_row(self):
        troop = self.alice.troops[0]
        self.assertEqual(len(self.battle.troops), 0)
        with self.assertRaises(OutOfBoundsException):
            self.battle.place_troop(troop, col=1, row=100000,
                                    outside=self.outside)

        self.assertEqual(len(self.battle.troops), 0)
        self.assertFalse(self.alice.troops[0].battle)

    def test_no_place_troop_off_board_col(self):
        troop = self.alice.troops[0]
        self.assertEqual(len(self.battle.troops), 0)
        with self.assertRaises(OutOfBoundsException):
            self.battle.place_troop(troop, col=-5000, row=1,
                                    outside=self.outside)

        self.assertEqual(len(self.battle.troops), 0)
        self.assertFalse(self.alice.troops[0].battle)

    def test_no_fight_ended_battle(self):
        """Can't fight in a battle that's over"""
        self.end_battle()

        troop = self.alice.troops[0]
        with self.assertRaises(BattleEndedException):
            self.battle.place_troop(troop, col=1, row=2, outside=self.outside)

    def test_no_fight_early_battle(self):
        with self.outside.db.session():
            battle2 = Battle.create(self.outside)

        troop = self.alice.troops[0]
        self.assertFalse(battle2.active)
        with self.assertRaises(BattleNotStartedException):
            battle2.place_troop(troop, col=1, row=2, outside=self.outside)
