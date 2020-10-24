from . import root_command, Command, BlockingExecuteCommand
from lxml import html
from stockbot.db import Base, Session
from sqlalchemy import Column, String, DateTime
import datetime
import hashlib
import logging
import requests

LOGGER = logging.getLogger(__name__)


class NewsArticleSeen(Base):

    __tablename__ = 'news_article_seen'

    id = Column(String, primary_key=True)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, id_):
        self.id = id_

    @classmethod
    def is_seen(cls, session, article, sender=None):
        return session.query(cls).filter_by(id=cls._article_key(article, sender)).all()

    @classmethod
    def mark_as_seen(cls, session, article, sender=None):
        o = cls(id_=cls._article_key(article, sender))
        session.add(o)
        session.flush()

    @classmethod
    def _article_key(cls, article, sender):
        if sender:
            return "{}-{}".format(article.key, sender)
        return article.key


class NewsArticle(object):

    def __init__(self, topic=None, url=None, headline=None, date_=None):
        self.topic = topic
        self.url = url
        self.headline = headline
        self.date_ = date_
        self.key = hashlib.sha224(url.encode('utf-8')).hexdigest()

    def __repr__(self):
        return "<NewsArticle key={}, topic={}, date_={}>".format(self.key, self.topic, self.date_)

    def __str__(self):
        return "Message: {} - {}, Date: {}, Link: {}".format(self.topic, self.headline, self.date_, self.url)


def get_articles(matches=(), sender=None):
    req = requests.get("https://www.avanza.se/placera/telegram.plc.html")
    req.raise_for_status()
    tree = html.fromstring(req.content)
    items = tree.xpath('//ul[@class="feedArticleList XSText"]/li[@class="item"]/a')
    for item in items:
        url_path = item.attrib["href"]
        absolute_url = "https://avanza.se{}".format(url_path)
        headline_date = item.find('span').text_content().lstrip().rstrip()
        headline = item.find('div').text_content()
        headline_split = headline.split(":")
        if len(headline_split) == 1:
            headline_topic = "unknown"
            headline_message = headline_split[0].lstrip().rstrip()
        else:
            headline_topic = headline_split[0].lower().lstrip().rstrip()
            headline_message = headline_split[1].lstrip().rstrip()
        if len(matches) == 0 or headline_topic in matches:
            session = Session()
            article = NewsArticle(headline_topic, absolute_url, headline_message, headline_date)
            try:
                if not NewsArticleSeen.is_seen(session, article, sender):
                    yield article
                    NewsArticleSeen.mark_as_seen(session, article, sender)
                    session.commit()
            except Exception as e:
                LOGGER.exception("Something went wrong when fetching news articles")
            finally:
                session.close()


def get(*args, **kwargs):
    sender = kwargs.get('sender', None)
    try:
        matches = [x.lower() for x in args[0].split(",")]
    except IndexError:
        matches = []
    try:
        return get_articles(matches, sender)
    except Exception as e:
        LOGGER.exception("Error", e)
        return "Broken: {}".format(e)


news_command = BlockingExecuteCommand(name="news", execute_command=get, help="<csv list of matches>",
                                      expected_num_args=1)
root_command.register(news_command)
