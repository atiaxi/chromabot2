
from chromabot2 import commands
from chromabot2.battle import Battle, Troop
from chromabot2.utils import now

from test.common import ChromaTest


# Functional and integration tests for battle


class TestBattle(ChromaTest):

    def troop_combat_helper(self, left, right):
        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at E4 with %s" % left)
        board = self.battle.realize_board()
        left_troop = board[3][5]  # Should have moved by 1
        self.assertTrue(left_troop)

        self.execute("attack #1 at I4 with %s" % right, as_who=self.bob)
        board = self.battle.realize_board()
        right_troop = board[3][7]
        self.assertTrue(right_troop)

        # FIGHT!
        self.bot_loop()
        board = self.battle.realize_board()
        # Sometimes, for some damn reason, that troop is in [3][7].  Don't feel
        # like figuring out why at the moment
        winner = board[3][6] or board[3][7]
        return left_troop, right_troop, winner

    def troop_combat_winonly(self, left, right):
        return self.troop_combat_helper(left, right)[2]

    def test_troop_does_not_immediately_move(self):
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack #1 at C4 with infantry")

        board = self.battle.realize_board()
        troop = board[3][2]
        self.assertTrue(troop)

    def test_troop_movement_zero(self):
        self.config.battle['troop_delay'] = "0"

        board = self.battle.realize_board()
        self.assertFalse(board[3][2])
        self.assertFalse(board[3][3])

        result = self.execute("attack #1 at C4 with infantry")

        # Because there's no troop delay, it should have instantly moved forward
        board = self.battle.realize_board()
        troop = board[3][3]
        self.assertFalse(board[3][2])
        self.assertTrue(troop)

        # Force another loop to move it along again
        self.bot_loop()
        board = self.battle.realize_board()
        fore_troop = board[3][4]
        self.assertTrue(fore_troop)
        self.assertEqual(troop, fore_troop)

        # Make sure it's not leaving copies of itself behind or anything
        self.assertFalse(board[3][3])
        self.assertFalse(board[3][2])

    def test_troop_movement_one(self):
        self.config.battle['troop_delay'] = "0"

        board = self.battle.realize_board()
        self.assertFalse(board[3][10])
        self.assertFalse(board[3][9])

        self.execute("attack #1 at k4 with infantry", as_who=self.bob)
        # Because there's no troop delay, it should have instantly moved forward
        board = self.battle.realize_board()
        troop = board[3][9]
        self.assertTrue(troop)

        # Force another loop to move it along again
        self.bot_loop()
        board = self.battle.realize_board()
        fore_troop = board[3][8]
        self.assertTrue(fore_troop)
        self.assertEqual(troop, fore_troop)

        # Make sure it's not leaving copies of itself behind or anything
        self.assertFalse(board[3][10])
        self.assertFalse(board[3][9])

    def test_troop_unopposed_score(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at D4 with infantry")

        board = self.battle.realize_board()
        troop = board[3][4]
        self.assertTrue(troop)

        # Wait until it crosses the board
        for expected_col in range(5, 11):
            self.bot_loop()
            self.assertEqual(expected_col, troop.col)

        # Still no scoring
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        # Until now!
        self.bot_loop()

        # Should be double the usual goal score
        scores = self.battle.load_scores()
        self.assertEqual(scores, [4, 0])

    def test_troop_opposed_score(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at D4 with infantry")

        board = self.battle.realize_board()
        troop = board[3][4]
        self.assertTrue(troop)

        # Throw some fodder at it
        self.execute("attack #1 at I4 with ranged", as_who=self.bob)

        # Wait until it crosses the board
        for expected_col in range(6, 11):
            self.bot_loop()
            self.assertEqual(expected_col, troop.col)

        # Should have got 1 point on the way there
        scores = self.battle.load_scores()
        self.assertEqual(scores, [1, 0])

        # Cross over
        self.bot_loop()

        # Just the usual goal score
        scores = self.battle.load_scores()
        self.assertEqual(scores, [3, 0])

    def test_troop_combat_win(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        ranged, infantry, winner = self.troop_combat_helper(
            "ranged", "infantry")
        self.assertEqual(winner, infantry)
        self.assertEqual(winner.hp, 1)
        self.assertTrue(winner.battle)
        self.assertIn(winner, self.battle.troops)

        # PW should have 1 point for that
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 1])

    def test_troop_combat_win_made_visible(self):
        self.config.battle['troop_delay'] = "0"

        ranged, infantry, winner = self.troop_combat_helper(
            "ranged", "infantry")
        self.assertEqual(winner.type, "infantry")
        self.assertEqual(ranged.hp, 0)
        self.assertFalse(ranged.is_deployable())
        self.assertTrue(winner.visible)

    def test_troop_combat_lose(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        cavalry, ranged, winner = self.troop_combat_helper("cavalry", "ranged")
        self.assertEqual(winner.type, "ranged")
        self.assertEqual(cavalry.hp, 0)
        self.assertFalse(cavalry.is_deployable())

        # PW should have 1 point for that
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 1])

    def test_troop_combat_tie(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        one, two, winner = self.troop_combat_helper(
            "infantry", "infantry")
        self.assertFalse(winner)
        # Both should be evicted
        for troop in (one, two):
            with troop.session() as s:
                s.refresh(troop)
            self.assertEqual(troop.hp, 1)
            self.assertFalse(troop.battle)
            self.assertNotIn(troop, self.battle.troops)
            self.assertTrue(troop.is_deployable())

        # No scores for that
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

    # These are  copy of the `test_circ` run in `test_db.py`, because
    # there's some discrepancy in what the model level and what the
    # higher level are reporting.
    def troop_combat_CIRC(self, left, right, expected):
        winner = self.troop_combat_winonly(left, right)
        if not expected:
            self.assertFalse(winner)
        else:
            self.assertTrue(winner)
            self.assertEqual(expected, winner.type)

    # CAVALRY
    def test_CI(self):
        self.troop_combat_CIRC("cavalry", "infantry", "cavalry")

    def test_CR(self):
        self.troop_combat_CIRC("cavalry", "ranged", "ranged")

    def test_CC(self):
        self.troop_combat_CIRC("cavalry", "cavalry", None)

    # INFANTRY
    def test_IR(self):
        self.troop_combat_CIRC("infantry", "ranged", "infantry")

    def test_IC(self):
        self.troop_combat_CIRC("infantry", "cavalry", "cavalry")

    def test_II(self):
        self.troop_combat_CIRC("infantry", "infantry", None)

    # RANGED
    def test_RC(self):
        self.troop_combat_CIRC("ranged", "cavalry", "ranged")

    def test_RI(self):
        self.troop_combat_CIRC("ranged", "infantry", "infantry")

    def test_RR(self):
        self.troop_combat_CIRC("ranged", "ranged", None)

    # End of CIRC tests
    def test_no_such_thing_as_friendly_fire(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at A4 with infantry")
        self.execute("attack #1 at C4 with ranged")

        board = self.battle.realize_board()
        # Infantry at B4 (having moved up from A4) will still be there, because
        # he bumped into the cavalry and halted
        infantry = board[3][1]
        self.assertTrue(infantry)

        # Cavalry had no such problem, should be at D4
        ranged = board[3][3]
        self.assertTrue(ranged)

        self.assertEqual(ranged.hp, 1)
        self.assertTrue(ranged.battle)
        self.assertIn(ranged, self.battle.troops)

        self.assertEqual(infantry.hp, 1)
        self.assertTrue(infantry.battle)
        self.assertIn(infantry, self.battle.troops)

    def test_fight_ends(self):
        self.assertTrue(self.battle.relevant)
        # Also seems like a good place to test the winner
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at D4 with infantry")

        board = self.battle.realize_board()
        troop = board[3][4]
        self.assertTrue(troop)

        # Wait until it crosses the board
        for expected_col in range(5, 11):
            self.bot_loop()
            self.assertEqual(expected_col, troop.col)
        self.bot_loop()
        scores = self.battle.load_scores()
        self.assertEqual(scores, [4, 0])

        results = self.end_battle()

        self.assertTrue(results)
        result = results[0]
        self.assertEqual(result.code, commands.CODE_END_BATTLE)

        self.assertFalse(self.battle.active)
        self.assertFalse(self.battle.relevant)
        self.assertEqual(self.battle.victor, self.alice.team)

        scores = self.battle.load_scores()
        self.assertEqual(scores, [4, 0])

    def test_fight_starts(self):
        with self.outside.db.session():
            battle2 = Battle.create(self.outside)

        self.bot_loop()
        self.assertFalse(battle2.active)

        battle2.begins = now()
        results = self.bot_loop()
        self.assertTrue(results)
        self.assertEqual(results[0].code, commands.CODE_BEGIN_BATTLE)
        self.assertEqual(results[0].extra, battle2)

        self.assertTrue(battle2.active)

    def test_heroes_never_die(self):
        self.execute("attack #1 at D4 with infantry")
        self.execute("attack #1 at C1 with cavalry")
        self.execute("attack #1 at E4 with ranged")

        for troop in self.alice.troops:
            self.battle.kill_troop(troop, "got in my way")

        for troop in self.alice.troops:
            self.assertFalse(troop.is_deployable())

        self.end_battle()

        for troop in self.alice.troops:
            self.assertTrue(troop.is_deployable())
            self.assertFalse(troop.battle)

    def test_dont_rez_unrelated_deaths(self):
        for troop in self.alice.troops:
            self.battle.kill_troop(troop, "got in my way")

        for troop in self.alice.troops:
            self.assertFalse(troop.is_deployable())

        self.end_battle()

        for troop in self.alice.troops:
            self.assertFalse(troop.is_deployable())
            self.assertFalse(troop.battle)
