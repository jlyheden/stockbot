import requests
import logging
from datetime import datetime
from stockbot.db import Base, Session
from lxml import etree
from sqlalchemy import Column, String, DateTime, Boolean, Integer, select, update
from sqlalchemy.exc import IntegrityError


LOGGER = logging.getLogger(__name__)


class RedditFreeGameHistory(Base):

    __tablename__ = 'reddit_free_game_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, index=True, unique=True)
    link = Column(String)
    published = Column(DateTime)
    seen = Column(Boolean)


class RedditFreeGamesService(object):

    def __init__(self, ignore_words: list = ()):
        self.ignore_words = ignore_words

    def refresh(self, session: Session) -> None:
        response = requests.get("https://www.reddit.com/r/FreeGameFindings/new.rss", headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        })
        response.raise_for_status()
        tree = etree.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        for entry in tree.findall('atom:entry', namespaces=ns):
            title = entry.find('atom:title', namespaces=ns).text
            content = entry.find('atom:content', namespaces=ns).text
            if any(word.lower() in title.lower() or word.lower() in content.lower() for word in self.ignore_words):
                LOGGER.info(f"Ignoring game: {title}")
                continue
            game = RedditFreeGameHistory(
                title=title,
                link=entry.find('atom:link', namespaces=ns).attrib["href"],
                published=datetime.fromisoformat(entry.find('atom:published', namespaces=ns).text),
                seen=False
            )
            session.add(game)
            try:
                session.commit()
            except IntegrityError:
                # Handle unique constraints, ask for forgiveness instead of permission
                session.rollback()

    @staticmethod
    def gimme(session: Session) -> list[RedditFreeGameHistory]:
        with session.begin():
            stmt = select(RedditFreeGameHistory).where(RedditFreeGameHistory.seen == False)
            results = session.execute(stmt).scalars().all()

            ids = [row.id for row in results]
            if ids:
                session.execute(
                    update(RedditFreeGameHistory)
                    .where(RedditFreeGameHistory.id.in_(ids))
                    .values(seen=True)
                )
            return results
