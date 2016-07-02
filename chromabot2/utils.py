import string
import time


def now():
    return time.mktime(time.localtime())


def col_to_letter(col):
    return string.ascii_uppercase[col]


def letter_to_col(letter):
    return string.ascii_lowercase.index(letter)
