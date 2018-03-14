import logging
import requests
import json

from urllib.parse import urlencode
from urllib.request import pathname2url
from datetime import datetime

from stockbot.provider.base import BaseQuoteService

LOGGER = logging.getLogger(__name__)


class BloombergQuote(object):

    def __init__(self, *args, **kwargs):
        data = kwargs.get('message', {})
        if "basicQuote" not in data:
            return
        for k, v in data["basicQuote"].items():
            if k == "lastUpdateEpoch":
                try:
                    setattr(self, "lastUpdateDatetime", datetime.fromtimestamp(int(v)).strftime("%Y-%m-%d %H:%M:%S"))
                except Exception as e:
                    LOGGER.exception("Failed to create attribute from lastUpdateEpoch")
            setattr(self, k, v)

    def __str__(self):
        return "Name: {n}, Price: {p}, Open Price: {op}, Low Price: {lp}, High Price: {hp}, Percent Change 1 Day: {p1d}, Update Time: {ut}"\
            .format(n=self.name, p=self.price, op=self.openPrice, lp=self.lowPrice, hp=self.highPrice,
                    p1d=self.percentChange1Day, ut=self.lastUpdateDatetime)

    def __getattribute__(self, item):
        try:
            # we cannot use this objects getattribute because then we loop until the world collapses
            return object.__getattribute__(self, item)
        except Exception as e:
            LOGGER.exception("Failed to look up attribute {}".format(item))
            return "N/A"

    def is_empty(self):
        try:
            return self.name == "N/A"
        except Exception:
            return True

    def is_fresh(self):
        if self.lastUpdateEpoch != "N/A":
            # most tickers are lagging 15 minutes so add another minute to avoid never getting "fresh" data
            return (datetime.now() - datetime.fromtimestamp(int(self.lastUpdateEpoch))).seconds < 16*60
        else:
            return False


class BloombergSearchResult(object):

    def __init__(self, *args, **kwargs):
        self.result = kwargs.get('result')["results"]

    def __str__(self):
        return "Result: {r}".format(r=" | ".join(
            ["Ticker: {t}, Country: {c}, Name: {n}, Type: {tt}".format(t=x.get("ticker_symbol", None),
                                                                       c=x.get("country", None),
                                                                       n=x.get("name", None),
                                                                       tt=x.get("resource_type", None))
             for x in self.result
             ]
        ))

    def result_as_list(self):
        return ["Ticker: {t}, Country: {c}, Name: {n}, Type: {tt}".format(t=x.get("ticker_symbol", None),
                                                                          c=x.get("country", None),
                                                                          n=x.get("name", None),
                                                                          tt=x.get("resource_type", None))
                for x in self.result
                ]

    def get_tickers(self):
        return [x.get("ticker_symbol", None) for x in self.result]

    def is_empty(self):
        return len(self.result) == 0


class BloombergQueryService(BaseQuoteService):

    # search results probably don't change that much so cache them
    search_cache = {}

    def __init__(self, *args, **kwargs):
        pass

    def get_quote(self, ticker):
        try:
            url = self.__quote_url(ticker)
            req = requests.get(url)
            if req.ok:
                j = json.loads(req.text)
                return BloombergQuote(message=j)
        except Exception as e:
            LOGGER.exception("Failed to retrieve stock quote")
            return None

    def search(self, query):
        if query not in self.search_cache:
            LOGGER.info("Response from query {q} not in cache, will query bloombergs search api".format(q=query))
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
                return BloombergSearchResult(result=j)
            else:
                raise Exception("Failed to query bloomberg search api. Code: {c}, Text: {t}".format(c=req.status_code,
                                                                                                    t=req.text))
        except Exception as e:
            LOGGER.exception("Failed to search for {q}, search url: {u}".format(q=query, u=url))
            raise

    @staticmethod
    def __quote_url(ticker):
        params = {
            "locale": "en"
        }
        path = "/markets/api/quote-page/{}".format(ticker)
        url = "https://www.bloomberg.com{path}?{params}".format(path=pathname2url(path), params=urlencode(params))
        LOGGER.debug("quote_url: {}".format(url))
        return url

    @staticmethod
    def __search_url(query):
        params = {
            "sites": "bbiz",
            "query": query
        }
        url = "https://search.bloomberg.com/lookup.json?{params}".format(params=urlencode(params))
        LOGGER.debug("search url: {}".format(url))
        return url
