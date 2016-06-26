#!/usr/bin/env python
import logging

from .bot import Chromabot
from .config import Config
from .outsiders import DebugOutsider


def main():
    # TODO: Probably a whole bunch of ways to configure an outsider by
    # command line switches or something
    conf = Config()
    outsider = DebugOutsider(conf)

    bot = Chromabot(outsider)
    bot.loop_forever()

if __name__ == '__main__':
    main()
