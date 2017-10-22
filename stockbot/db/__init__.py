from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from stockbot.configuration import Configuration

Base = declarative_base()

engine = create_engine(Configuration().database_url)
Session = sessionmaker(bind=engine)


def create_tables():
    Base.metadata.create_all(engine)


def drop_tables():
    Base.metadata.drop_all(engine)
