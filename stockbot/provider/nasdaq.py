import requests
from lxml.html.soupparser import fromstring
from sqlalchemy import Column, Integer, String

from stockbot.db import Base


class NasdaqCompany(Base):

    __tablename__ = 'nasdaq_companies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    ticker = Column(String, index=True, unique=True)
    currency = Column(String)
    category = Column(String)
    segment = Column(String, index=True)

    def __init__(self, name, ticker, currency, category, segment):
        self.name = name
        self.ticker = ticker.replace(" ", "-")
        self.currency = currency
        self.category = category
        self.segment = segment

    def __repr__(self):
        return "<NasdaqCompany(name='{name}', ticker='{ticker}', currency='{currency}', category='{category}', segment='{segment}')>".\
            format(name=self.name, ticker=self.ticker, currency=self.currency, category=self.category,
                   segment=self.segment)

    def __eq__(self, other):
        return self.name == other


class NasdaqIndexScraper(object):

    indexes = {
        "Nordic Large Cap": "http://www.nasdaqomxnordic.com/shares/listed-companies/nordic-large-cap",
        "Nordic Mid Cap": "http://www.nasdaqomxnordic.com/shares/listed-companies/nordic-mid-cap",
        "Nordic Small Cap": "http://www.nasdaqomxnordic.com/shares/listed-companies/nordic-small-cap"
    }

    def scrape(self, i):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"
        }
        res = requests.get(self.indexes[i], headers=headers)
        tree = fromstring(res.text)
        companies = tree.xpath("//article[@class='nordic-our-listed-companies']//tbody/tr")
        rv = []
        for company in companies:
            fields = company.findall("td")
            name = fields[0].find("a").text
            ticker = fields[1].text
            currency = fields[2].text
            category = fields[4].text
            rv.append(NasdaqCompany(name=name, ticker=ticker, currency=currency, category=category, segment=i))
        return rv
