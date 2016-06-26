import logging
import time


from .commands import Result
from .db import ChromaException
from .parser import parse
from .battle import Battle


class Chromabot:

    def __init__(self, outside):
        self.outside = outside
        self.running = True
        fmt = "%(asctime)s: %(levelname)s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)

    def loop_forever(self):
        while self.running:
            self.loop_once()

    def loop_once(self):
        results = []
        outside = self.outside
        messages = outside.get_messages()
        if messages is None:
            self.running = False
        else:
            logging.info("Handling messages")

            for message in messages:
                logging.info("Handling: %s" % message)
                command = parse(message.raw_text)
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
        if delay:
            logging.info("Sleeping for %d seconds" % delay)
            time.sleep(delay)
        logging.debug("Results: %s", results)
        return results

    def frame(self):
        results = []

        logging.info("Updating battles")
        with self.outside.db.session() as s:
            battles = s.query(Battle).filter_by(relevant=True)

        for battle in battles:
            logging.info("Updating battle %d", battle.id)
            results.extend(result for result in battle.update(self.outside))

        return results
