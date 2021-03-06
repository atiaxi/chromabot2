from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from .battle import Troop
from .db import Base
from .utils import now


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    team = Column(Integer)
    # region_id = Column(Integer, ForeignKey('regions.id'))
    leader = Column(Integer, default=0)
    defectable = Column(Boolean, default=True)
    # This default is the now() time from chromabot1
    recruited = Column(Integer, default=1376615874)

    troops = relationship("Troop", back_populates="owner")

    @classmethod
    def create(cls, db, name, team, leader=False):
        result = cls(name=name, team=team, leader=leader, defectable=True,
                     recruited=now())
        # TODO: Put this user in the correct region
        with db.session() as s:
            s.add(result)

        # Assign this user some troops
        Troop.infantry(result)
        Troop.cavalry(result)
        Troop.ranged(result)

        return result

    def defect(self, team):
        with self.session():
            self.team = team

    def __repr__(self):
        return "<User(name='%s', team='%d')>" % (
            self.name, self.team)


# A generic key-value store for quick lookups.  Currently only used by the
# reddit outsider
class KeyValue(Base):
    __tablename__ = "keyval"

    # Strings as primary keys are apparently still not that great, so this one
    # will have an int id too.
    id = Column(Integer, primary_key=True)
    namespace = Column(String)
    key = Column(String)
    value = Column(Text)

    def __repr__(self):
        return "<KeyValue(namespace=%s, key=%s)>" % (self.namespace, self.key)
