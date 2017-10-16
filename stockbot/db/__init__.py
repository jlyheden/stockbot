from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from stockbot.configuration import Configuration

Base = declarative_base()

engine = create_engine(Configuration().database)
Session = sessionmaker(bind=engine)


def create_tables():
    Base.metadata.create_all(engine)
