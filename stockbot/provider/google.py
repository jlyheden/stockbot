import json
import requests
import logging
import re

from urllib.parse import urlencode
from stockbot.db import Base
from sqlalchemy import Column, Integer, String, Float

LOGGER = logging.getLogger(__name__)


class StockDomain(Base):

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    ticker = Column(String, index=True, unique=True)
    net_profit_margin_last_q = Column(Float)
    net_profit_margin_last_y = Column(Float)
    operating_margin_last_q = Column(Float)
    operating_margin_last_y = Column(Float)
    ebitd_margin_last_q = Column(Float)
    ebitd_margin_last_y = Column(Float)

    # return on average asset
    roaa_last_q = Column(Float)
    roaa_last_y = Column(Float)

    # return on average equity
    roae_last_q = Column(Float)
    roae_last_y = Column(Float)

    market_cap = Column(String)
    price_to_earnings = Column(Float)
    beta = Column(Float)
    earnings_per_share = Column(Float)

    dividend_yield = Column(Float)
    latest_dividend = Column(Float)

    def from_google_finance_quote(self, gfq):
        """

        :param gfq:
        :type gfq: GoogleFinanceQuote
        :return:
        """
        self.name = gfq.name
        self.ticker = gfq.symbol

        for r in gfq.keyratios:
            if r["title"] == "Net profit margin":
                self.net_profit_margin_last_q = self.__safe_to_float(r, "recent_quarter")
                self.net_profit_margin_last_y = self.__safe_to_float(r, "annual")
            elif r["title"] == "Operating margin":
                self.operating_margin_last_q = self.__safe_to_float(r, "recent_quarter")
                self.operating_margin_last_y = self.__safe_to_float(r, "annual")
            elif r["title"] == "EBITD margin":
                self.ebitd_margin_last_q = self.__safe_to_float(r, "recent_quarter")
                self.ebitd_margin_last_y = self.__safe_to_float(r, "annual")
            elif r["title"] == "Return on average assets":
                self.roaa_last_q = self.__safe_to_float(r, "recent_quarter")
                self.roaa_last_y = self.__safe_to_float(r, "annual")
            elif r["title"] == "Return on average equity":
                self.roae_last_q = self.__safe_to_float(r, "recent_quarter")
                self.roae_last_y = self.__safe_to_float(r, "annual")

        self.market_cap = gfq.mc
        self.price_to_earnings = self.__safe_to_float(gfq, "pe")
        self.beta = self.__safe_to_float(gfq, "beta")
        self.earnings_per_share = self.__safe_to_float(gfq, "eps")
        self.dividend_yield = self.__safe_to_float(gfq, "dy")
        self.latest_dividend = self.__safe_to_float(gfq, "ldiv")

    @staticmethod
    def __safe_to_float(d, key):
        try:
            if type(d) is dict:
                value = d.get(key)
            else:
                value = getattr(d, key, "0")
            value = re.sub("[^-\d.]", "", value)
            LOGGER.debug("Got this value '{}' for key '{}'".format(value, key))
            return float(value)
        except ValueError as e:
            LOGGER.exception("failed to set value to float, key '{key}'".format(key=key))
            return float(0)

    def __repr__(self):
        return "<StockDomain({})>".format(", ".join(["{}={}".format(x, getattr(self, x)) for x in
                                                     StockDomain.__table__.columns._data.keys()]))

    def fields(self):
        rv = []
        for attr, value in self.__dict__.items():
            if not callable(attr) and not attr.startswith("_"):
                rv.append(attr)
        return rv


class GoogleFinanceQuote(object):

    def __init__(self, *args, **kwargs):
        pattern = re.compile("^[0-9,.]+$")
        data = kwargs.get('message', {})
        for k, v in data.items():
            # remove + from price change if positive
            if k == 'c' or k == 'cp':
                v = v.lstrip("+")
            elif k == 'dy' and len(v) > 0:
                v = "{}%".format(v)
            # remove comma from values
            if isinstance(v, str):
                if pattern.match(v):
                    v = v.replace(",", "")
                # don't set attributes that are empty, it will look ugly
                if len(v) == 0:
                    continue
            setattr(self, k, v)

    def __str__(self):
        return "Name: {n}, Price: {p}, Open Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change: {p1d}"\
            .format(n=self.name, p=self.l, op=self.op, lp=self.lo, hp=self.hi, p1d=self.cp)

    def __getattribute__(self, item):
        try:
            # we cannot use this objects getattribute because then we loop until the world collapses
            return object.__getattribute__(self, item)
        except Exception as e:
            LOGGER.exception("Failed to look up attribute '{}'".format(item))
            return "N/A"

    def fundamentals(self, duration):
        _key_ratios = ["{t}: {r}".format(t=x["title"], r=x[duration].replace(",", ""))
                       for x in self.keyratios
                       if "title" in x and duration in x and x["title"] != "Employees"
                       and len(x[duration]) > 0]

        _date_key_name =  "kr_{}_date".format(duration)
        if hasattr(self, _date_key_name) and len(_key_ratios) > 0:
            _key_ratios.append("Date: {}".format(getattr(self, _date_key_name)))

        flatten_keyratios = ", ".join(_key_ratios) if len(_key_ratios) > 0 else "Error: duration not found"

        return "Name: {n}, P/E: {pe}, Yield: {y}, Beta: {b}, Earnings Per Share: {eps}, {fl}".format(
            n=self.name, pe=self.pe, y=self.dy, b=self.beta, eps=self.eps, fl=flatten_keyratios)


class GoogleFinanceSearchResult(object):

    def __init__(self, *args, **kwargs):
        self.result = kwargs.get('result')["matches"]

    def __str__(self):
        return "Result: {r}".format(r=" | ".join(
            ["Ticker: {t}, Market: {m}, Name: {n}".format(t=x["t"], m=x["e"], n=x["n"]) for x in self.result]
        ))

    def result_as_list(self):
        return ["Ticker: {t}, Market: {m}, Name: {n}".format(t=x["t"], m=x["e"], n=x["n"]) for x in self.result]

    def is_empty(self):
        return len(self.result) == 0


class GoogleFinanceQueryService(object):

    # search results probably don't change that much so cache them
    search_cache = {}

    def get_quote(self, ticker):
        try:
            url = self.__quote_url(ticker)
            req = requests.get(url)
            if req.ok:
                j = json.loads(req.content[6:-2].decode('unicode_escape'))
                return GoogleFinanceQuote(message=j)
        except Exception as e:
            LOGGER.exception("Failed to get quote for '{ticker}'".format(ticker=ticker))
            return GoogleFinanceQuote()

    def search(self, query):
        if query not in self.search_cache:
            LOGGER.info("Response from query {q} not in cache, will query google finance search api".format(q=query))
            try:
                self.search_cache[query] = self.__search_query(query)
            except Exception as e:
                return None
        return self.search_cache[query]

    def __search_query(self, query):
        url = self.__search_url(query)
        try:
            req = requests.get(url)
            if req.ok:
                j = json.loads(req.text)
                return GoogleFinanceSearchResult(result=j)
            else:
                raise Exception("Failed to query google finance search api. Code: {c}, Text: {t}".format(
                    c=req.status_code, t=req.text))
        except Exception as e:
            LOGGER.exception("Failed to search for {q}, search url: {u}".format(q=query, u=url))
            raise

    def __quote_url(self, ticker):
        params = {
            "q": ticker,
            "output": "json"
        }
        url = "https://finance.google.com/finance?{params}".format(params=urlencode(params))
        LOGGER.debug("quote_url: {}".format(url))
        return url

    def __search_url(self, query):
        params = {
            "matchtype": "matchall",
            "q": query
        }
        url = "https://finance.google.com/finance/match?{params}".format(params=urlencode(params))
        LOGGER.debug("search_url: {}".format(url))
        return url
