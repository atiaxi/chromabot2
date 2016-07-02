#!/usr/bin/env python
import argparse
import logging

from .bot import Chromabot
from .config import Config
from .reddit import RedditOutsider  # Just so it gets registered
from .outsiders import all_outsiders


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("-o", "--outsider",
                      default="debug",
                      choices=all_outsiders.keys(),
                      help="The Outsider to use for the bot")
    argp.add_argument("-c", "--conf",
                      default=None,
                      help="Configuration file location")
    group = argp.add_mutually_exclusive_group()
    group.add_argument("-d", "--debug",
                       action="store_true",
                       help="Set log level to DEBUG")
    group.add_argument("-v", "--verbose",
                       action="store_true",
                       help="Set log level to INFO")
    args = argp.parse_args()
    level = logging.WARN
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO

    fmt = "%(asctime)s: %(levelname)s %(message)s"
    logging.basicConfig(level=level, format=fmt)

    logging.debug("Debug enabled")
    logging.info("Info enabled")

    conf = Config(args.conf)

    outsider = all_outsiders[args.outsider](conf)
    bot = Chromabot(outsider)
    bot.loop_forever()

if __name__ == '__main__':
    main()
