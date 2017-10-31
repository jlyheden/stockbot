from sqlalchemy import Column, String
from stockbot.db import Session, Base
import collections


class ScheduledTicker(Base):

    __tablename__ = "scheduled_tickers"

    ticker = Column(String, primary_key=True)

    def __repr__(self):
        return "<ScheduledTicker(ticker={})>".format(self.ticker)


class ScheduledCommand(Base):

    __tablename__ = "scheduled_command"

    command = Column(String, primary_key=True)

    def __repr__(self):
        return "<ScheduledCommand(command={})>".format(self.command)


def db_session(func):
    """
    decorator that will inject an sqlalchemy session and always close it after
    the decorated function has completed
    :param func:
    :return:
    """
    def func_wrapper(self, *args, **kwargs):
        self.session = Session()
        res = func(self, *args, **kwargs)
        self.session.close()
        return res
    return func_wrapper


class DatabaseCollection(collections.Iterable, list):

    """
    Funky custom list implementation that will deal with database persistence
    """
    def __init__(self, *args, **kwargs):
        super(DatabaseCollection, self).__init__()
        self.type = kwargs.get('type')
        self.attribute = kwargs.get('attribute', None)

    def __setitem__(self, index, value):
        raise NotImplemented

    @db_session
    def __getitem__(self, index):
        all_items = self.session.query(self.type).all()
        if self.attribute is not None:
            return getattr(all_items[index], self.attribute)
        return all_items[index]

    @db_session
    def __len__(self):
        all_items = self.session.query(getattr(self.type, self.attribute)).count()
        return all_items

    def __delitem__(self, index):
        raise NotImplemented

    def insert(self, index, value):
        raise NotImplemented

    @db_session
    def append(self, value):
        if isinstance(value, self.type):
            self.session.add(value)
            self.session.commit()
        else:
            item = self.type()
            setattr(item, self.attribute, value)
            self.session.add(item)
            self.session.commit()

    @db_session
    def remove(self, value):
        ticker = self.session.query(self.type).get(value)
        self.session.delete(ticker)
        self.session.commit()

    @db_session
    def __iter__(self):
        all_items = self.session.query(self.type).all()
        for item in all_items:
            yield getattr(item, self.attribute)

    @db_session
    def __contains__(self, item):
        ticker = self.session.query(self.type).get(item)
        return ticker is not None
