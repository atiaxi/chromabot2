from chromabot2 import commands
from chromabot2.battle import Battle, Troop

from test.common import ChromaTest

# These tests skirt closer to the functional side, as they're putting
# commands through the parse->Command->execute pipeline, but they're not
# full integration tests.


class TestSkirmish(ChromaTest):

    def test_basic_attack(self):
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        results = self.execute("attack #1 at C4 with infantry")
        self.assertTrue(results)
        self.assertEqual(results[0].code, commands.CODE_OK)

        board = self.battle.realize_board()
        self.assertTrue(board[3][2])

    def test_refer_nonexistent_battle(self):
        self.fail_to_execute("attack #9999 at C4 with infantry",
                             err_text="Battle 9999 does not exist!")

    def test_infer_battle(self):
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack at C4 with infantry")

        board = self.battle.realize_board()
        self.assertTrue(board[3][2])

    def test_could_not_infer_battle(self):
        with self.outside.db.session():
            battle2 = Battle.create(self.outside)
            battle2.active = True
        self.assertTrue(battle2)

        err = ("There is more than one battle underway; you must specify "
               "which one to participate in.")
        self.fail_to_execute("attack at C4 with infantry",
                             err_text=err)

    def test_no_infer_battle_when_no_battle(self):
        with self.outside.db.session():
            self.battle.active = False

        self.fail_to_execute("attack at C4 with infantry",
                             err_text="There are no battles underway!")

    def test_outsider_infer_battle(self):
        # Ordinarily, we wouldn't be able to resolve this
        with self.outside.db.session():
            battle2 = Battle.create(self.outside)
            battle2.active = True
        self.assertTrue(battle2)
        # But the outsider knows what battle this is!
        self.outside.battle = self.battle

        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack at C4 with infantry")

        board = self.battle.realize_board()
        self.assertTrue(board[3][2])

    def test_refer_to_other_battle(self):
        with self.outside.db.session():
            battle2 = Battle.create(self.outside)
            battle2.active = True

        board = battle2.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack #%d at C4 with infantry" % battle2.id)

        board = battle2.realize_board()
        self.assertTrue(board[3][2])

    def test_refer_nonexistent_type(self):
        self.fail_to_execute("attack at C4 with fobble",
                             err_text="Could not find any free 'fobble' troops")
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

    def test_refer_codeword(self):
        self.skipTest("Not yet implemented")

    def test_out_of_troops(self):
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack #1 at C4 with infantry")

        board = self.battle.realize_board()
        self.assertTrue(board[3][2])

        self.fail_to_execute(
            "attack #1 at C1 with infantry",
            err_text="Could not find any free 'infantry' troops")
        self.assertFalse(board[3][0])

    def test_second_troop(self):
        # First, give alice another infantry a troop
        Troop.infantry(self.alice)
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack #1 at C4 with infantry")

        board = self.battle.realize_board()
        inf1 = board[3][2]
        self.assertTrue(inf1)

        self.execute("attack #1 at C1 with infantry")

        board = self.battle.realize_board()
        inf2 = board[0][2]
        self.assertTrue(inf2)

        self.assertNotEqual(inf1.id, inf2.id)
        self.assertEqual(inf1.type, inf2.type)

    def test_skip_dead_troop(self):
        # First, give alice another infantry a troop
        Troop.infantry(self.alice)
        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack #1 at C4 with infantry")

        board = self.battle.realize_board()
        inf1 = board[3][2]
        self.assertTrue(inf1)

        self.battle.kill_troop(inf1, "is lost in time and space")

        board = self.battle.realize_board()
        self.assertFalse(board[3][2])

        self.execute("attack #1 at C4 with infantry")

        board = self.battle.realize_board()
        inf2 = board[3][2]
        self.assertTrue(inf2)

        self.assertNotEqual(inf1.id, inf2.id)


