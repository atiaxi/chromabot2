import unittest

from pyparsing import ParseException

from chromabot2.battle import SkirmishCommand
from chromabot2.parser import parse


class TestSkirmish(unittest.TestCase):

    def test_skirmish(self):
        src = "attack at A1 with infantry"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'a')
        self.assertEqual(parsed.raw_row, '1')
        self.assertEqual(parsed.troop_type, "infantry")

    def test_skirmish_convert(self):
        src = "attack at C5 with infantry"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.col, 2)
        self.assertEqual(parsed.row, 4)
        self.assertEqual(parsed.troop_type, "infantry")

    def test_convert_zero(self):
        src = "attack at C0 with infantry"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.col, 2)
        self.assertEqual(parsed.row, 0)
        self.assertEqual(parsed.troop_type, "infantry")

    def test_skirmish_with_comma(self):
        src = "attack at A,1 with infantry"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'a')
        self.assertEqual(parsed.raw_row, '1')
        self.assertEqual(parsed.troop_type, "infantry")

    def test_skirmish_with_battle(self):
        src = "attack #7 at A1 with infantry"

        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'a')
        self.assertEqual(parsed.raw_row, '1')
        self.assertEqual(parsed.troop_type, "infantry")
        self.assertEqual(parsed.battle_id, 7)

    def test_oppose(self):
        src = "oppose at A1 with infantry"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'a')
        self.assertEqual(parsed.raw_row, '1')
        self.assertEqual(parsed.troop_type, "infantry")

    def test_support(self):
        src = "support at A1 with infantry"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'a')
        self.assertEqual(parsed.raw_row, '1')
        self.assertEqual(parsed.troop_type, "infantry")

    def test_attack_with_bad_type(self):
        src = "attack at Q12 with zorple"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'q')
        self.assertEqual(parsed.raw_row, '12')
        self.assertEqual(parsed.troop_type, "zorple")

    def test_attack_with_codeword(self):
        src = "attack at N5 with a rubber chicken"
        parsed = parse(src)
        self.assertIsInstance(parsed, SkirmishCommand)
        self.assertEqual(parsed.raw_col, 'n')
        self.assertEqual(parsed.raw_row, '5')
        self.assertEqual(parsed.troop_type, "a rubber chicken")

    def test_column_only_one_char(self):
        src = "attack at AZ1 with infantry"
        with self.assertRaises(ParseException):
            parse(src)

    def test_row_must_be_number(self):
        src = "attack at A,X with infantry"
        with self.assertRaises(ParseException):
            parse(src)

    def test_no_unicode_col(self):
        src = "attack at ☃3 with infantry"
        with self.assertRaises(ParseException):
            parse(src)
