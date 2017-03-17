import logging
import time

from pyparsing import ParseException

from .commands import Result
from .db import ChromaException
from .parser import parse
from .battle import Battle


class Chromabot:

    def __init__(self, outside):
        self.outside = outside
        self.running = True
        self.started = False

    def loop_forever(self):
        logging.info("Bot started up")
        while self.running:
            self.loop_once()

    def loop_once(self):
        results = []
        outside = self.outside

        outside.config.refresh()

        if not self.started:
            self.started = True
            outside.startup()

        logging.info("Checking for recruits")
        outside.handle_recruits()

        messages = outside.get_messages()
        if messages is None:
            self.running = False
        else:
            logging.info("Handling messages")

            for message in messages:
                logging.info("Handling: %s" % message)
                command = None
                try:
                    command = parse(message.raw_text)
                except ParseException as pe:
                    result = Result.from_exception(pe, message)
                if command:
                    try:
                        result = command.execute(message)
                    except ChromaException as e:
                        result = Result.from_exception(e, message)
                if result:
                    results.append(result)

            results.extend(self.frame())
            outside.report_results(results)
        delay = outside.config.bot.getint('sleep', fallback=0)
        logging.debug("Results: %s", results)
        if delay:
            logging.info("Sleeping for %d seconds" % delay)
            time.sleep(delay)
        return results

    def frame(self):
        results = []

        with self.outside.db.session() as s:
            battles = s.query(Battle).filter_by(relevant=True).all()

        logging.info("Checking to see if eternal battle needs to start")
        if not battles:
            eternal = Battle.create(self.outside)
            logging.info("Eternal battle created, id %s !", eternal.id)

        logging.info("Updating battles")
        for battle in battles:
            logging.info("Updating battle %d", battle.id)
            results.extend(result for result in battle.update(self.outside))

        return results
