#!/usr/bin/env python

from chromabot2.battle import Troop
from chromabot2.config import Config
from chromabot2.db import DB
from chromabot2.models import User


def main():
    c = Config()

    dbconn = DB(c)
    with dbconn.session() as s:
        users = s.query(User)

        for user in users:
            print("Adding troops for %s" % user.name)
            for _ in range(4):
                Troop.infantry(user)
                Troop.cavalry(user)
                Troop.ranged(user)

if __name__ == '__main__':
    main()
