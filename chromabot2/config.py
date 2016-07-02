import logging
import os.path
from configparser import ConfigParser


class Config(object):

    def __init__(self, conffile=None):
        # Try to locate our configuration directory

        self.conffile = None
        self.data = {}

        proposals = [conffile, os.environ.get("CHROMABOT_CONFIG"),
                     "../config/config.ini", "./config/config.ini",
                     "/etc/chromabot/config.ini"]

        if not self.check_exist(proposals):
            logging.critical("Could not locate config file!")
            raise FileNotFoundError("Unable to locate config file")

        self.refresh()

    def __contains__(self, item):
        return item in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __getattr__(self, key):
        return self.data[key]

    def check_exist(self, proposed_paths):
        for fullpath in proposed_paths:
            if fullpath and os.path.exists(fullpath):
                self.conffile = fullpath
                return True
        return False

    def get(self, key, default=None):
        return self.data.get(key, default)

    def refresh(self):
        with open(self.conffile) as data_file:
            self.data = ConfigParser()
            self.data.read(self.conffile, encoding='utf8')
        logging.info("Loaded config file from %s", self.conffile)
