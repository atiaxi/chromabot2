
from chromabot2 import commands
from chromabot2.battle import Battle, Troop
from chromabot2.utils import now

from test.common import ChromaTest


# Functional and integration tests for battle


class TestBattle(ChromaTest):

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

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at E4 with ranged")
        board = self.battle.realize_board()
        ranged = board[3][5]  # Should have moved by 1
        self.assertTrue(ranged)

        self.execute("attack #1 at I4 with infantry", as_who=self.bob)
        board = self.battle.realize_board()
        infantry = board[3][7]
        self.assertTrue(infantry)

        # FIGHT!
        self.bot_loop()

        board = self.battle.realize_board()
        winner = board[3][6]
        self.assertEqual(winner, infantry)

        self.assertEqual(winner.hp, 1)
        self.assertTrue(winner.battle)
        self.assertIn(winner, self.battle.troops)

        # PW should have 1 point for that
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 1])

    def test_troop_combat_lose(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at E4 with cavalry")
        board = self.battle.realize_board()
        cavalry = board[3][5]  # Should have moved by 1
        self.assertTrue(cavalry)

        self.execute("attack #1 at I4 with ranged", as_who=self.bob)
        board = self.battle.realize_board()
        ranged = board[3][7]
        self.assertTrue(ranged)

        # FIGHT!
        self.bot_loop()
        board = self.battle.realize_board()
        self.assertEqual(board[3][6], ranged)
        self.assertEqual(cavalry.hp, 0)
        self.assertFalse(cavalry.is_deployable())

        # PW should have 1 point for that
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 1])

    def test_troop_combat_tie(self):
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

        self.config.battle['troop_delay'] = "0"
        self.execute("attack #1 at E4 with infantry")
        board = self.battle.realize_board()
        infantry = []
        infantry.append(board[3][5])  # Should have moved by 1
        self.assertTrue(infantry[0])

        self.execute("attack #1 at I4 with infantry", as_who=self.bob)
        board = self.battle.realize_board()
        infantry.append(board[3][7])
        self.assertTrue(infantry[1])

        # FIGHT!
        self.bot_loop()

        # Both should be evicted
        board = self.battle.realize_board()
        self.assertFalse(board[3][6])
        for team in range(2):
            troop = infantry[team]
            with troop.session() as s:
                s.refresh(troop)
            self.assertEqual(troop.hp, 1)
            self.assertFalse(troop.battle)
            self.assertNotIn(troop, self.battle.troops)
            self.assertTrue(troop.is_deployable())

        # No scores for that
        scores = self.battle.load_scores()
        self.assertEqual(scores, [0, 0])

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

    def test_error_reporting(self):
        results = self.execute("attack #1 at Z9999 with infantry",
                               assert_pass=False)
        for result in results:
            self.assertFalse(result.success)
            self.assertEqual(result.text, "That row is not on the board!")
            self.assertEqual(result.code, commands.CODE_NOK)

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
