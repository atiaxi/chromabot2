#!/usr/bin/env python
import argparse
import code
import logging
import readline
import sys

sys.path.append(".")
sys.path.append("./chromabot2")

from chromabot2.config import Config
from chromabot2.reddit import RedditOutsider

from chromabot2.db import *
from chromabot2.models import *
from chromabot2.battle import Battle, Troop
from chromabot2.utils import *


# QUERY HELPERS
def all(cls, **kw):
    return query(cls, **kw).all()


def all_as_dict(cls):
    result = {}
    for item in all(cls):
        result[item.name] = item
    return result

def by_id(cls, id):
    result = query(cls, id=id).first()
    print(result)
    return result


def by_name(cls, name):
    result = query(cls, name=name).first()
    print(result)
    return result


def first(cls, **kw):
    return query(cls, **kw).first()


def query(cls, **kw):
    with db.session() as sess:
        return sess.query(cls).filter_by(**kw)


# TODO: Re-create cancel battle


def end_battle(battle):
    battle.end()
    # TODO:  call the reddit outsider to update stuff


# TODO: Re-create fast_battle

def timestr(secs=None):
    if secs is None:
        secs = time.mktime(time.localtime())
    return time.strftime("%Y-%m-%d %H:%M:%S GMT",
                          time.gmtime(secs))


def commit():
    with db.session():
        pass


def main():
    global db

    argp = argparse.ArgumentParser()
    argp.add_argument("-c", "--conf",
                      default=None,
                      help="Configuration file location")
    args = argp.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    config = Config(args.conf)
    outsider = RedditOutsider(config)
    db = outsider.db
    
    vars = globals().copy()
    vars.update(locals())
    shell = code.InteractiveConsole(vars)
    shell.interact("Chromabot2 CLI ready")

if __name__ == "__main__":
    main()
