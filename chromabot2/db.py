from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session


# Base class for all the exceptions we want to catch and report
class ChromaException(Exception):
    pass


# Base classes for DB stuff and the DB object itself:
class Model(object):

    @contextmanager
    def session(self):
        session = Session.object_session(self)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise


Base = declarative_base(cls=Model)


class DB:
    def __init__(self, config):
        self.engine = create_engine(config.bot["dbstring"], echo=False)
        self.sessionfactory = sessionmaker(bind=self.engine)
        self._session = None

    def create_all(self):
        Base.metadata.create_all(self.engine)

    def drop_all(self):
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self):
        if not self._session:
            self._session = self.sessionfactory()
        try:
            yield self._session
            self._session.commit()
        except:
            self._session.rollback()
            raise

    @contextmanager
    def new_session(self):
        sess = self.sessionfactory()
        try:
            yield sess
            sess.commit()
        except:
            sess.rollback()
            raise
        finally:
            sess.close()
