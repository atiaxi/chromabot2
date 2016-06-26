#!/usr/bin/env python
from chromabot2.config import Config
from chromabot2.db import DB
from chromabot2.models import User


def main():
    c = Config()

    dbconn = DB(c)
    dbconn.drop_all()
    dbconn.create_all()

    # Basic users
    User.create(dbconn, 'reostra', 0, True)
    User.create(dbconn, 'fakey', 1, True)

    # sess = dbconn.session()
    #
    # source = sys.argv[1]
    # regions = Region.create_from_json(sess, json_file=source)
    #
    # # Create team DB entries
    # TeamInfo.create_defaults(sess, c)
    #
    # stamp()

if __name__ == '__main__':
    main()
